import asyncio
import json

import httpx
import pytest

from heschema.experiments import _score, run_decoding
from heschema.jsonio import digest, loads
from heschema.providers import Generation, Provider, content_has_reasoning_markers

CASE = {'id': 'control', 'family': 'control', 'contract': {'id': 'control', 'version': '1', 'schema': {'type': 'object'}},
        'prompt': 'Return n=1.', 'expected': {'n': 1}}


@pytest.mark.parametrize('setting,sent', [('false', False), ('true', True), ('low', 'low'), ('default', None)])
def test_ollama_controls_are_explicit_frozen_and_fingerprint_the_submitted_body(setting, sent, monkeypatch):
    monkeypatch.setenv('OLLAMA_THINK', setting)
    observed = []
    def handler(request):
        observed.append(json.loads(request.content))
        return httpx.Response(200, json={'model': 'test-model', 'message': {'content': '{"n":1}', 'thinking': 'separate'},
                                        'done_reason': 'stop', 'prompt_eval_count': 7, 'eval_count': 3})
    async def check():
        provider = Provider('ollama', model='test-model', interval=0, transport=httpx.MockTransport(handler))
        monkeypatch.setenv('OLLAMA_THINK', 'changed-after-construction')
        try:
            g = await provider.generate([], seed=42)
            if sent is None:
                assert 'think' not in observed[0]
            else:
                assert observed[0]['think'] == sent and type(observed[0]['think']) is type(sent)
            assert g.metadata['requestControls']['thinkingRequested'] == sent
            assert g.metadata['requestControls']['payloadHash'] == digest(observed[0])
            assert g.reasoning == 'separate' and g.text == '{"n":1}'
            assert 'Authorization' not in json.dumps(g.metadata)
        finally:
            await provider.close()
    asyncio.run(check())


def test_invalid_ollama_control_is_rejected_before_creating_client(monkeypatch):
    monkeypatch.setenv('OLLAMA_THINK', 'typo')
    with pytest.raises(ValueError, match='OLLAMA_THINK'):
        Provider('ollama')


def test_reasoning_marker_is_not_extracted_and_markers_inside_json_are_valid_data(tmp_path):
    text = '<think>reasoning</think>\n{"n":1}'
    assert content_has_reasoning_markers(text)
    assert not content_has_reasoning_markers('{"literal":"<think>"}')
    class Backend:
        name, model, interval, thinking = 'ollama', 'test-model', 0, False
        async def generate(self, messages, *args, **kwargs):
            return Generation(text, model=self.model, metadata={'resolvedModelConfirmed': True, 'finish_reason': 'stop',
                                                               'requestControls': {'thinkingRequested': False}})
    report = asyncio.run(run_decoding([CASE], Backend(), tmp_path, max_requests=3))
    assert report['complete'] and report['empiricalLLMEvidence']
    assert not report['comparisonValid'] and not report['designValid']
    assert len(report['controlChecks']['thinkingMismatchRows']) == 3
    rows = [json.loads(line) for line in (tmp_path / 'runs.jsonl').read_text().splitlines()]
    assert all(r['attempts'][0]['generation']['text'] == text for r in rows)
    assert all('thinking_control_mismatch' in r['firstObservations']['categories'] for r in rows)
    assert report['arms']['prompt_only']['firstPassSuccess']['numerator'] == 0


def test_semantic_numeric_oracle_does_not_penalize_storage_representation():
    evaluation = {'stages': {'json': 'valid'}, 'parsed': {'n': 1.0}, 'accepted': True, 'semanticValid': None, 'intentScope': 'not_checked'}
    assert _score(evaluation, CASE)['success']
    assert not _score({**evaluation, 'parsed': {'n': True}}, CASE)['success']


def test_extreme_numbers_are_range_failures_without_silent_underflow():
    from heschema.contracts import Contract
    from heschema.failure_categories import classify
    from heschema.schema import SchemaEngine
    from heschema.validation import validate_contract
    engine = SchemaEngine()
    try:
        for raw in ('1e1000000', '1e-1000000', '-1.2e-99999999999999999'):
            e = validate_contract(raw, engine, Contract('number', '1', {'type': 'number'}))
            assert e['jsonValid'] is False
            assert classify(e)['categories'] == ['numeric_range']
        assert loads('0e-1000000') == 0
        assert loads('-0.00e-1000000') == 0
        assert loads('5e-324') != 0
    finally:
        engine.close()


def test_initial_and_final_stage_reports_differ_after_repair(tmp_path):
    from heschema.experiments import run_repair_study
    class Backend:
        name, model, interval = 'mock', 'stub', 0
        good = False
        async def generate(self, messages, *args, **kwargs):
            return Generation('{"n":1}' if self.good else 'prose', model=self.model,
                              metadata={'resolvedModelConfirmed': True, 'finish_reason': 'stop', 'synthetic': True})
    async def check():
        p = Backend()
        await run_decoding([CASE], p, tmp_path / 'first')
        p.good = True
        report = await run_repair_study([CASE], p, tmp_path / 'first', tmp_path / 'repair', budgets=[1])
        arm = report['bySourceMode']['prompt_only']['actionable:1']
        assert arm['stages']['json']['amongAttempts']['numerator'] == 0
        assert arm['finalStages']['json']['amongAttempts']['numerator'] == 1
        assert arm['firstFailureCategories']['categories']['json_syntax']['numerator'] == 1
        assert arm['finalFailureCategories']['categories'] == {}
        assert arm['recovery']['numerator'] == 1
    asyncio.run(check())


def test_category_report_keeps_models_separate_and_refuses_mixed_datasets(tmp_path):
    from heschema.category_reports import category_report
    class Backend:
        name, model, interval = 'mock', 'first-model', 0
        async def generate(self, messages, *args, **kwargs):
            return Generation('{"n":1}', model=self.model, metadata={'resolvedModelConfirmed': True, 'synthetic': True})
    async def check():
        p = Backend()
        await run_decoding([CASE], p, tmp_path / 'a')
        p.model = 'second-model'
        await run_decoding([CASE], p, tmp_path / 'b')
    asyncio.run(check())
    paths = [tmp_path / name / 'report.json' for name in ('a', 'b')]
    report = category_report(paths)
    assert len(report['rows']) == 6 and report['pooledAccuracy'] is None
    assert {r['requestedModel'] for r in report['rows']} == {'first-model', 'second-model'}
    assert all(not r['empiricalLLMEvidence'] for r in report['rows'])
    changed = json.loads(paths[1].read_text())
    changed['config']['datasetHash'] = 'different'
    paths[1].write_text(json.dumps(changed))
    with pytest.raises(ValueError, match='datasetHash'):
        category_report(paths)
