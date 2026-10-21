"""Crash boundaries must preserve evidence and must not authorize a replacement call."""

import asyncio
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from heschema.jsonio import canonical, read_json
from heschema.providers import Generation, ProviderError
from heschema.repair import RepairLimits, coordinate
from heschema.study_evidence import EvidenceError, StudyEvidence, append_jsonl

SLOT = {'caseId': 'real-record-test-control', 'repeat': 0, 'arm': 'compact'}


def evaluate(g):
    return {'success': g.text == '{"ok":true}', 'accepted': g.text == '{"ok":true}', 'errors': []}


def generate(text='{"ok":true}', inp=11, out=7):
    return Generation(text, inp, out, 'test-stub', metadata={'finish_reason': 'stop'})


def commit(store, result, slot=SLOT):
    row = {'caseId': slot['caseId'], 'repeat': slot['repeat'], 'arm': slot['arm'], 'status': 'ok', **result}
    return store.session(slot).commit(row, result)


def run(store, *, generated=None, evaluator=evaluate, limits=None):
    async def request(messages, index):
        assert read_json(next(store.requests.glob('*.json')))['state'] == 'started'
        return generated or generate()
    return asyncio.run(coordinate(request, evaluator, [], evidence=store.session(SLOT), limits=limits))


def test_response_is_synced_before_validation_and_status_commit(tmp_path):
    store = StudyEvidence(tmp_path)
    raw = ' \n{"ok":true}\t'
    g = generate(raw)
    g.reasoning = 'PRIVATE_REASONING_TEST_MARKER'
    g.metadata['rateLimitHeaders'] = {'x-header': 'PRIVATE_HEADER_TEST_MARKER'}
    def check(response):
        record = read_json(next(store.requests.glob('*.json')))
        assert record['state'] == 'returned' and record['generation']['text'] == raw
        assert record['generation']['input_tokens'] == 11
        assert not list(store.results.glob('*.json'))
        return evaluate(response)
    result = run(store, generated=g, evaluator=check)
    row = commit(store, result)
    with (tmp_path / 'runs.jsonl').open('a') as stream:
        append_jsonl(stream, row)
    assert store.load_rows() == [row]
    audit = store.audit()
    assert audit['evidenceComplete'] and audit['observedReturnedUsage']['input_tokens']['total'] == 11
    private = ''.join(path.read_text() for path in store.requests.glob('*.json'))
    assert 'PRIVATE_' not in private


def test_subprocess_crash_after_response_leaves_raw_evidence_before_evaluation(tmp_path):
    # A real abrupt process exit, with no finally block or result-status write.
    code = '''
import asyncio, os, sys
from heschema.providers import Generation
from heschema.repair import coordinate
from heschema.study_evidence import StudyEvidence
store = StudyEvidence(sys.argv[1])
async def request(messages, attempt):
    return Generation('  {"n": 1}\\n', 23, 8, 'test-stub')
def evaluate(g):
    os._exit(17)
asyncio.run(coordinate(request, evaluate, [], evidence=store.session({'caseId': 'crash'})))
'''
    result = subprocess.run([sys.executable, '-c', code, str(tmp_path)], check=False,
                            env={**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src')})
    assert result.returncode == 17
    store = StudyEvidence(tmp_path)
    record = read_json(next(store.requests.glob('*.json')))
    assert record['generation']['text'] == '  {"n": 1}\n'
    assert record['generation']['input_tokens'] == 23
    audit = store.audit()
    assert audit['issues'][0]['status'] == 'result_missing'
    assert audit['observedReturnedUsage']['input_tokens']['total'] == 23
    with pytest.raises(EvidenceError, match='No requests resumed'):
        store.load_rows()


def test_committed_result_recovers_without_regeneration_after_log_write_crash(tmp_path):
    store = StudyEvidence(tmp_path)
    row = commit(store, run(store))
    assert not (tmp_path / 'runs.jsonl').exists()
    assert store.load_rows() == [row]
    assert store.load_rows() == [row]  # recovery appends once
    assert len((tmp_path / 'runs.jsonl').read_text().splitlines()) == 1


def test_missing_unknown_usage_is_not_zero_or_complete(tmp_path):
    store = StudyEvidence(tmp_path)
    row = commit(store, run(store, generated=generate(inp=None)))
    assert row['evidence']['status'] == 'usage_missing'
    assert row['attempts'][0]['generation']['input_tokens'] is None
    audit = store.audit()
    assert audit['recordsVerified'] and not audit['evidenceComplete']
    assert audit['returnedUsageMissing'] == 1
    assert audit['observedReturnedUsage']['input_tokens'] == {'knownSubtotal': 0, 'missing': 1, 'total': None}


@pytest.mark.parametrize('damage', ['delete', 'text', 'tokens', 'ledger', 'truncate'])
def test_deleted_corrupt_or_mismatched_evidence_blocks_resume(tmp_path, damage):
    store = StudyEvidence(tmp_path)
    row = commit(store, run(store))
    store.load_rows()
    path = next(store.requests.glob('*.json'))
    if damage == 'delete':
        path.unlink()
    elif damage == 'truncate':
        (tmp_path / 'runs.jsonl').write_text(canonical(row)[:-1])
    elif damage == 'ledger':
        wrong = copy.deepcopy(row)
        wrong['requestLedger'][0]['evidenceRef'] = {'id': '0' * 32, 'sha256': 'wrong'}
        (tmp_path / 'runs.jsonl').write_text(canonical(wrong) + '\n')
    else:
        record = read_json(path)
        record['generation']['text' if damage == 'text' else 'input_tokens'] = 'tampered'
        path.write_text(json.dumps(record))
    assert not store.audit()['recordsVerified']
    with pytest.raises(EvidenceError, match='No requests resumed'):
        store.load_rows()


def test_durable_write_failure_prevents_evaluation_and_completion(tmp_path, monkeypatch):
    from heschema import study_evidence
    store = StudyEvidence(tmp_path)
    original = study_evidence.atomic_json
    def broken(path, value):
        if value.get('state') == 'returned':
            raise OSError('disk full test')
        original(path, value)
    monkeypatch.setattr(study_evidence, 'atomic_json', broken)
    def never(g):
        pytest.fail('Evaluation must not run before durable response save')
    with pytest.raises(OSError, match='disk full'):
        run(store, evaluator=never)
    assert not list(store.results.glob('*.json'))
    assert store.audit()['issues'][0]['status'] == 'response_missing_unknown_outcome'


def test_interrupted_repair_keeps_initial_response_and_unknown_request(tmp_path):
    store = StudyEvidence(tmp_path)
    async def request(messages, index):
        if index == 0:
            return generate('{}')
        raise RuntimeError('simulated process interruption')
    def check(g):
        return {'accepted': False, 'errors': [{'code': 'bad', 'message': 'fix'}]}
    with pytest.raises(RuntimeError, match='interruption'):
        asyncio.run(coordinate(request, check, [], limits=RepairLimits(1), evidence=store.session(SLOT),
                               feedback_selector=lambda e: e['errors']))
    audit = store.audit()
    assert audit['requestsByState'] == {'returned': 1, 'replayed': 0, 'failed': 0, 'started': 1}
    assert {issue['status'] for issue in audit['issues']} == {'result_missing', 'response_missing_unknown_outcome'}
    assert audit['observedReturnedUsage']['input_tokens']['total'] == 11


def test_provider_rejection_is_explicit_and_not_a_fabricated_response(tmp_path):
    store = StudyEvidence(tmp_path)
    async def request(messages, index):
        raise ProviderError('HTTP 400', code='request_rejected', status=400)
    result = asyncio.run(coordinate(request, evaluate, [], evidence=store.session(SLOT)))
    commit(store, result)
    assert store.audit()['requestsByState']['failed'] == 1
    record = read_json(next(store.requests.glob('*.json')))
    assert record['failure']['httpStatus'] == 400 and 'generation' not in record


def test_legacy_rows_and_pending_schedule_stay_explicit(tmp_path):
    store = StudyEvidence(tmp_path)
    store.set_schedule([SLOT])
    audit = store.audit()
    assert audit['missingResultSlots'] == [SLOT] and audit['scheduleComplete'] is False
    assert audit['availability'] == 'no_verifiable_results'
    (tmp_path / 'runs.jsonl').write_text('{"status":"ok","firstPassSuccess":true}\n')
    assert store.audit()['issues'] == [{'row': 0, 'status': 'legacy_unverified'}]
    with pytest.raises(EvidenceError):
        store.load_rows()


def test_async_workers_keep_separate_requests_and_replayed_usage_is_not_new(tmp_path):
    store = StudyEvidence(tmp_path)
    async def one(index):
        slot = {**SLOT, 'caseId': str(index)}
        async def request(messages, attempt):
            await asyncio.sleep(0)
            return generate()
        result = await coordinate(request, evaluate, [], first_generation=generate('{}', 99, 77),
                                  limits=RepairLimits(1), evidence=store.session(slot),
                                  feedback_selector=lambda e: [{'code': 'bad', 'message': 'fix'}])
        return commit(store, result, slot)
    async def workers():
        return await asyncio.gather(*(one(i) for i in range(4)))
    rows = asyncio.run(workers())
    assert len(rows) == 4 and all(row['requestsAttempted'] == 1 for row in rows)
    audit = store.audit()
    assert audit['evidenceComplete'] and audit['requestsByState']['returned'] == 4
    assert audit['requestsByState']['replayed'] == 4
    assert audit['observedReturnedUsage']['input_tokens']['total'] == 44


def test_benchmark_recovers_committed_status_without_reissuing_provider_call(tmp_path, monkeypatch):
    from heschema.benchmark import run as benchmark
    from heschema.dataset import generate_cases
    from heschema.study_evidence import EvidenceSession
    case = generate_cases()[0]
    class Fake:
        name, model, interval = 'mock', 'test-stub', 0
        calls = 0
        async def generate(self, *args, **kwargs):
            self.calls += 1
            return generate(canonical(case['expected']))
    original = EvidenceSession.commit
    def interrupted(session, row, recovery):
        original(session, row, recovery)
        raise RuntimeError('after durable result before progress')
    provider = Fake()
    monkeypatch.setattr(EvidenceSession, 'commit', interrupted)
    with pytest.raises(RuntimeError, match='before progress'):
        asyncio.run(benchmark([case], provider, tmp_path, repeats=1, repairs=0))
    assert provider.calls == 1
    monkeypatch.setattr(EvidenceSession, 'commit', original)
    report = asyncio.run(benchmark([case], provider, tmp_path, repeats=1, repairs=0))
    assert provider.calls == 3  # Three arms total, never a replacement fourth call.
    assert report['complete'] and report['evidence']['evidenceComplete']


def test_decoding_marks_missing_usage_and_audit_needs_no_provider(tmp_path, monkeypatch, capsys):
    from test_controlled_experiments import CASE, Fake

    from heschema.cli import main
    from heschema.experiments import run_decoding
    class NoUsage(Fake):
        async def generate(self, *args, **kwargs):
            result = await super().generate(*args, **kwargs)
            result.input_tokens = None
            return result
    report = asyncio.run(run_decoding([CASE], NoUsage(), tmp_path, modes=['prompt_only']))
    assert not report['designValid'] and not report['evidence']['evidenceComplete']
    assert report['evidence']['returnedUsageMissing'] == 1
    monkeypatch.setattr(sys, 'argv', ['heschema', 'evidence-audit', str(tmp_path)])
    with pytest.raises(SystemExit) as stopped:
        main()
    assert stopped.value.code == 1
    assert json.loads(capsys.readouterr().out)['returnedUsageMissing'] == 1
