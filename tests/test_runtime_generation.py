import asyncio

import pytest
from fastapi.testclient import TestClient
from test_relationships import INVOICE

from heschema.api import create_app
from heschema.cli_integration import execute_cli_recovery
from heschema.jsonio import canonical
from heschema.providers import Generation
from heschema.schema import SchemaEngine


@pytest.mark.parametrize('prompt_style', ['full', 'compact'])
def test_contract_generation_repair_and_partial_evidence(tmp_path, monkeypatch, prompt_style):
    monkeypatch.delenv('HESCHEMA_API_TOKEN', raising=False)
    outputs = [{'quantity': 2, 'unitPriceMinor': 1250, 'totalMinor': 25}, {'quantity': 2, 'unitPriceMinor': 1250, 'totalMinor': 2500}]
    seen = []
    async def fake(self, messages, *args, **kwargs):
        seen.append((messages, kwargs))
        return Generation(canonical(outputs[min(len(seen)-1, 1)]), model='mock', metadata={'finish_reason': 'stop', 'synthetic': True})
    monkeypatch.setattr('heschema.providers.Provider.generate', fake)
    with TestClient(create_app(tmp_path / 'state.sqlite')) as client:
        assert client.post('/contracts', json=INVOICE.as_dict()).status_code == 201
        ctx = client.post('/contexts', json={'contractId': 'invoice', 'contractVersion': '1', 'data': {'quantity': 2, 'unitPriceMinor': 1250}, 'approvedPointers': ['/quantity', '/unitPriceMinor']}).json()
        client.post(f"/contexts/{ctx['id']}/confirm", json={'version': 1})
        result = client.post('/contracts/generate', json={'contractId': 'invoice', 'contractVersion': '1', 'contextId': ctx['id'], 'contextVersion': 1, 'prompt': 'Prepare invoice', 'provider': 'mock', 'repairs': 1, 'promptStyle': prompt_style}).json()
        assert result['validation']['success'] and result['repair']['requestsAttempted'] == 2
        assert result['repair']['feedbackVersion'] == 'category-v1'
        assert result['timing']['scope'] == 'contract_generation_handler'
        assert result['timing']['totalMs'] >= result['repair']['timing']['totalMs']
        assert result['repair']['timing']['localEvaluationMs'] >= 0
        # This test replaces generate(), so its provider phases are uninstrumented.
        assert result['repair']['timing']['providerResponseMs'] is None
        assert result['repair']['attempts'][0]['repairFeedback']['message'] == seen[1][0][-1]['content']
        assert result['promptStyle'] == prompt_style
        assert seen[0][1]['retry'] is False
        assert result['capability']['keywordEnforcement'] == 'unknown'
        assert not result['executionAuthorized']
        assert client.post('/contracts/generate', json={'contractId': 'invoice', 'contractVersion': '1', 'prompt': 'Invoice', 'provider': 'openai', 'mode': 'native_original'}).status_code == 422


def test_cli_recovery_uses_multiple_calls_and_never_relabels_report_as_output(monkeypatch):
    calls = []
    async def cli(**kwargs):
        calls.append(kwargs)
        return {'exitCode': 1 if len(calls) == 1 else 0, 'elapsedMs': 1,
                'parsedJson': {'document': {'n': 'wrong' if len(calls) == 1 else 1}}, 'stdout': '{}'}
    monkeypatch.setattr('heschema.cli_integration.execute_cli_run', cli)
    r = asyncio.run(execute_cli_recovery(schema={'type': 'object', 'properties': {'n': {'type': 'integer'}}}, prompt='n=1', model='test', mode='native_schema', engine=SchemaEngine(), repairs=1))
    assert len(calls) == 2 and r['diagnostics']['heschemaSchemaValid']
    assert r['requestUnit'] == 'cli_invocations' and r['upstreamRequestsObserved'] is None
    assert 'validation failures' in calls[1]['prompt']
