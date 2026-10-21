"""Analysis weights tasks; public export excludes private transport/reasoning data."""

import asyncio
import copy
import json
import runpy
from datetime import datetime, timezone
from pathlib import Path

import pytest

from heschema.confirmation import PACK, sha, valid_outputs
from heschema.confirmation_run import run_slot
from heschema.jsonio import canonical
from heschema.providers import Generation

ANALYSIS = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/analyze_confirmation.py'))
PAIRED = ANALYSIS['paired_analysis']
EXPORT = ANALYSIS['export']
FENCED = ANALYSIS['fenced_payload_diagnostic']
RESUME = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/resume_confirmation.py'))['prepare_resume']


def pair(case_id, cluster, repeat, full, compact):
    return [{'complete': True, 'caseId': case_id, 'cluster': cluster,
             'model': 'analysis-test', 'repeat': repeat, 'arm': arm,
             'firstCorrect': value, 'finalCorrect': value}
            for arm, value in (('full', full), ('compact', compact))]


def test_task_weighting_prevents_repeats_becoming_independent_tasks():
    rows = [row for repeat in range(9) for row in pair('a', 'source-a', repeat, False, True)]
    rows += pair('b', 'source-b', 0, True, False)
    result = PAIRED(rows, repeats=100)['outcomes']['finalCorrect']
    assert result['meanTaskDifferencePp'] == 0
    assert result['compactWins'] == 9 and result['fullWins'] == 1
    assert result['sourceClusters'] == 2
    assert result['clusterBootstrap95Pp'] == [-100, 100]


def test_ceiling_sample_does_not_imply_population_error_is_zero():
    result = PAIRED(pair('a', 'source-a', 0, True, True), repeats=100)
    assert result['outcomes']['finalCorrect']['clusterBootstrap95Pp'] == [0, 0]
    assert 'does not prove zero population error' in result['notice']


def test_incomplete_or_unpaired_results_do_not_enter_paired_effect():
    rows = pair('a', 'source-a', 0, True, True)
    rows[1]['complete'] = False
    result = PAIRED(rows, repeats=100)['outcomes']['firstCorrect']
    assert result['matchedPairs'] == 0 and result['meanTaskDifferencePp'] is None


def test_markdown_diagnostic_never_changes_strict_success():
    from heschema.confirmation import oracle
    case = json.loads((PACK / 'cases.json').read_text())[0]
    text = '```json\n' + canonical(valid_outputs(case)[0]) + '\n```'
    assert FENCED(case, text) is True
    assert oracle(case, text) is False
    assert FENCED(case, '{}') is None
    assert FENCED(case, '```json\n{}\n```') is False


def test_quota_observer_does_not_retain_provider_error_body():
    import httpx
    observer = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/confirmation_quota_log.py'))
    response = httpx.Response(429, json={'error': {'message': 'Tokens per day (TPD) on org PRIVATE_ORG_TEST_MARKER'}},
                              headers={'retry-after': '120', 'x-ratelimit-limit-tokens': '8000',
                                       'authorization': 'PRIVATE_HEADER_TEST_MARKER'})
    record = observer['quota_record'](response, 'test-only')
    assert record['categories'] == ['tokens_per_day']
    assert 'PRIVATE' not in canonical(record)
    assert record['headers'] == {'retry-after': '120', 'x-ratelimit-limit-tokens': '8000'}
    assert observer['quota_record'](httpx.Response(200, json={}), 'test-only') is None


def test_export_is_scoped_and_does_not_publish_reasoning_or_headers(tmp_path):
    cases = json.loads((PACK / 'cases.json').read_text())
    protocol = json.loads((PACK / 'protocol.json').read_text())
    case = cases[0]
    model = protocol['models'][0]

    class Fake:
        async def generate(self, messages, seed, max_tokens, temperature, retry=True):
            return Generation(canonical(valid_outputs(case)[0]), input_tokens=50, output_tokens=10,
                              model=model, reasoning='PRIVATE_REASONING_TEST_MARKER',
                              metadata={'finish_reason': 'stop', 'resolvedModelConfirmed': True,
                                        'rateLimitHeaders': {'secret-header': 'PRIVATE_HEADER_TEST_MARKER'}})

    row = asyncio.run(run_slot(Fake(), case,
                              {'caseId': case['id'], 'model': model, 'repeat': 0, 'arm': 'full'}, protocol))
    row.update(worker=0, recordedAt=datetime.now(timezone.utc).isoformat(), dispatchWaitMs=0,
               freezeSha256=sha(PACK / 'freeze.json'))
    (tmp_path / 'config.json').write_text(json.dumps({'freezeSha256': row['freezeSha256'], 'protocol': protocol}))
    (tmp_path / 'runs.jsonl').write_text(canonical(row) + '\n')
    (tmp_path / 'summary.json').write_text('{}')
    target = tmp_path / 'export'
    result = EXPORT(tmp_path, target)
    assert result['completedSlots'] == 1
    public = '\n'.join(p.read_text() for p in target.iterdir())
    assert 'PRIVATE_REASONING_TEST_MARKER' not in public
    assert 'PRIVATE_HEADER_TEST_MARKER' not in public
    response = json.loads((target / 'responses.jsonl').read_text())
    assert response['text'] == canonical(valid_outputs(case)[0])
    assert response['correct'] is True
    assert 'textSha256' in response

    wrong = copy.deepcopy(row)
    wrong['result']['attempts'][0]['generation']['model'] = 'offline-stub'
    (tmp_path / 'runs.jsonl').write_text(canonical(wrong) + '\n')
    with pytest.raises(ValueError, match='unconfirmed or mock'):
        EXPORT(tmp_path, tmp_path / 'no-export')

    wrong = copy.deepcopy(row)
    wrong['recordedAt'] = '2000-01-01T00:00:00+00:00'
    (tmp_path / 'runs.jsonl').write_text(canonical(wrong) + '\n')
    with pytest.raises(ValueError, match='predates'):
        EXPORT(tmp_path, tmp_path / 'no-export')


def test_slower_resume_preserves_original_evidence_and_protocol(tmp_path):
    root = Path(__file__).resolve().parents[1]
    previous = tmp_path / 'previous'
    previous.mkdir()
    runtime = 'src/heschema/confirmation_run.py'
    config = {'freezeSha256': sha(PACK / 'freeze.json'), 'interval': 10,
              'codeHashes': {runtime: sha(root / runtime)}}
    (previous / 'config.json').write_text(json.dumps(config))
    (previous / 'summary.json').write_text('{"completedSlots": 12}')
    original = '{"opaque": "preserved evidence"}\n'
    (previous / 'runs.jsonl').write_text(original)
    target = tmp_path / 'resumed'
    RESUME(previous, target, 20)
    assert (previous / 'runs.jsonl').read_text() == original
    assert (target / 'runs.jsonl').read_text() == original
    assert not (target / 'config.json').exists()  # execute must create a fresh verified config.
    history = json.loads((target / 'session_history.json').read_text())
    assert history[0]['priorConfig'] == config
    assert history[0]['nextWorkerIntervalSeconds'] == 20
    with pytest.raises(ValueError, match='new destination'):
        RESUME(previous, target, 20)
    with pytest.raises(ValueError, match='slower pacing'):
        RESUME(previous, tmp_path / 'faster', 5)
    config['codeHashes'][runtime] = 'changed'
    (previous / 'config.json').write_text(json.dumps(config))
    with pytest.raises(ValueError, match='Runtime changed'):
        RESUME(previous, tmp_path / 'changed', 20)
