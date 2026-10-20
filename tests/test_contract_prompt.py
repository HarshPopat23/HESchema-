import copy
import json

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from test_relationships import CTX, INVOICE

from heschema.api import create_app
from heschema.context_schema import effective_schema, trusted_information
from heschema.contract_prompt import contract_messages
from heschema.contracts import Contract, generation_envelope
from heschema.jsonio import canonical
from heschema.providers import Generation
from heschema.state import StateStore
from heschema.validation import envelope

GOOD = {'quantity': 2, 'unitPriceMinor': 1250, 'totalMinor': 2500}


def test_full_prompt_preserves_existing_content_and_compact_keeps_facts_once():
    city = 'approved-destination-' * 100
    contract = Contract('trip', '1', {
        'type': 'object', 'properties': {'city': {'type': 'string'}}, 'required': ['city'],
    }, bindings=[{'instanceLocation': '/city', 'contextLocation': '/city'}])
    snapshot = {**CTX, 'data': {'city': city, 'private': 'not-approved'},
                'approvedPointers': ['/city']}
    before = copy.deepcopy((contract.as_dict(), snapshot))
    effective, evidence = effective_schema(contract, snapshot)
    full = contract_messages(contract, snapshot, evidence, effective, 'Plan a trip')
    assert full == [{'role': 'system', 'content':
        'Return only whole JSON. Never execute tools. Use clarification for missing information '
        'and preserve refusals. Authoritative output schema: ' + canonical(effective)
        + '\nDeclared application relationships: ' + canonical(contract.relationships)
        + '\nApproved bindings: ' + canonical(evidence['activeBindings'])
        + '\nTrusted facts: ' + canonical(trusted_information(snapshot))},
        {'role': 'user', 'content': 'Plan a trip'}]
    compact = contract_messages(contract, snapshot, evidence, contract.schema,
                                'Plan a trip', style='compact')
    assert full[0]['content'].count(city) == 3
    assert compact[0]['content'].count(city) == 1
    assert 'not-approved' not in compact[0]['content']
    assert len(compact[0]['content']) < len(full[0]['content'])
    assert (contract.as_dict(), snapshot) == before
    with pytest.raises(ValueError, match='Unknown contract prompt style'):
        contract_messages(contract, snapshot, evidence, contract.schema, 'Trip', style='typo')


@pytest.mark.parametrize('style', ['full', 'compact'])
@pytest.mark.parametrize('mode', ['prompt_only', 'native_original', 'native_projected'])
@pytest.mark.parametrize('output,failed_stage', [
    (GOOD, None),
    ({**GOOD, 'quantity': 3, 'totalMinor': 3750}, 'context'),
    ({**GOOD, 'totalMinor': 25}, 'relationships'),
    ({**GOOD, 'totalMinor': '2500'}, 'originalSchema'),
])
def test_all_generation_paths_keep_full_local_validation(
        tmp_path, monkeypatch, style, mode, output, failed_stage):
    monkeypatch.delenv('HESCHEMA_API_TOKEN', raising=False)
    seen = []
    async def fake(self, messages, *args, **kwargs):
        seen.append((copy.deepcopy(messages), kwargs))
        return Generation(canonical(output), model='mock', metadata={'finish_reason': 'stop'})
    monkeypatch.setattr('heschema.providers.Provider.generate', fake)
    with TestClient(create_app(tmp_path / 'state.sqlite')) as client:
        assert client.post('/contracts', json=INVOICE.as_dict()).status_code == 201
        ctx = client.post('/contexts', json={
            'contractId': INVOICE.id, 'contractVersion': INVOICE.version,
            'data': CTX['data'], 'approvedPointers': CTX['approvedPointers'],
        }).json()
        assert client.post(f"/contexts/{ctx['id']}/confirm", json={'version': 1}).status_code == 200
        response = client.post('/contracts/generate', json={
            'contractId': INVOICE.id, 'contractVersion': INVOICE.version,
            'contextId': ctx['id'], 'contextVersion': 1, 'prompt': 'Prepare invoice',
            'provider': 'mock', 'mode': mode, 'promptStyle': style,
        })
        assert response.status_code == 200, response.text
        result = response.json()
    assert result['promptStyle'] == style and not result['executionAuthorized']
    assert result['repair']['requestsAttempted'] == 1
    decision = result['validation']
    assert decision['accepted'] is (failed_stage is None)
    if failed_stage:
        assert decision['stages'][failed_stage] == 'invalid'
    else:
        assert decision['result'] == 'PASS'
    messages, kwargs = seen[0]
    assert canonical(INVOICE.relationships) in messages[0]['content']
    if mode == 'prompt_only':
        assert 'format_schema' not in kwargs
    else:
        schema = kwargs['format_schema']
        wrong_source = {**GOOD, 'quantity': 3, 'totalMinor': 3750}
        assert Draft202012Validator(schema).is_valid(GOOD)
        # COMPACT does not outsource context checks to provider schema enforcement.
        assert Draft202012Validator(schema).is_valid(wrong_source) is (style == 'compact')
        if mode == 'native_projected':
            assert result['projection']['effectiveHash']


def test_compact_bindings_preserve_keywords_nested_paths_and_missing_approval(tmp_path, monkeypatch):
    monkeypatch.delenv('HESCHEMA_API_TOKEN', raising=False)
    schema = {'type': 'object', 'properties': {
        'a/b~c': {'type': 'array', 'items': {'type': 'string'}},
        'score': {'type': 'number'}, 'choice': {'type': 'string'},
        'unapproved': {'type': 'string'},
    }}
    contract = Contract('bounds', '1', schema, bindings=[
        {'instanceLocation': '/a~1b~0c/0', 'contextLocation': '/city'},
        {'instanceLocation': '/score', 'contextLocation': '/low', 'keyword': 'minimum'},
        {'instanceLocation': '/score', 'contextLocation': '/high', 'keyword': 'maximum'},
        {'instanceLocation': '/choice', 'contextLocation': '/choices', 'keyword': 'enum'},
        {'instanceLocation': '/unapproved', 'contextLocation': '/private', 'required': False},
    ])
    good = {'a/b~c': ['Goa'], 'score': 3, 'choice': 'train'}
    output = good
    seen = []
    async def fake(self, messages, *args, **kwargs):
        seen.append(copy.deepcopy(messages))
        return Generation(canonical(output), metadata={'finish_reason': 'stop'})
    monkeypatch.setattr('heschema.providers.Provider.generate', fake)
    with TestClient(create_app(tmp_path / 'state.sqlite')) as client:
        assert client.post('/contracts', json=contract.as_dict()).status_code == 201
        ctx = client.post('/contexts', json={
            'contractId': contract.id, 'contractVersion': contract.version,
            'data': {'city': 'Goa', 'low': 2, 'high': 5, 'choices': ['train', 'bus'],
                     'private': 'not-approved'},
            'approvedPointers': ['/city', '/low', '/high', '/choices'],
        }).json()
        client.post(f"/contexts/{ctx['id']}/confirm", json={'version': 1})
        body = {'contractId': contract.id, 'contractVersion': contract.version,
                'contextId': ctx['id'], 'contextVersion': 1, 'prompt': 'Prepare',
                'provider': 'mock', 'promptStyle': 'compact'}
        assert client.post('/contracts/generate', json=body).json()['validation']['success']
        content = seen[0][0]['content']
        assert 'not-approved' not in content and '"/private"' not in content
        bindings = json.loads(content.split('\nApproved bindings: ')[1].split('\n')[0])
        assert bindings == contract.bindings[:-1]
        for wrong in [
            {**good, 'a/b~c': ['Pune']}, {**good, 'score': 1},
            {**good, 'score': 6}, {**good, 'choice': 'flight'},
        ]:
            output = wrong
            result = client.post('/contracts/generate', json=body).json()['validation']
            assert not result['accepted'] and result['stages']['context'] == 'invalid'


@pytest.mark.parametrize('action', ['call_tool', 'ask_clarification', 'refuse'])
def test_compact_tool_envelopes_preserve_controls_and_required_context(tmp_path, monkeypatch, action):
    monkeypatch.delenv('HESCHEMA_API_TOKEN', raising=False)
    contract = Contract('tool-invoice', '1', INVOICE.schema, 'tool_envelope', 'prepare_invoice',
                        bindings=INVOICE.bindings, relationships=INVOICE.relationships)
    seen = []
    async def fake(self, messages, *args, **kwargs):
        seen.append(messages)
        output = envelope(action, tool=contract.tool if action == 'call_tool' else None,
                          arguments=GOOD if action == 'call_tool' else {},
                          missing=['quantity'] if action == 'ask_clarification' else [])
        return Generation(canonical(output), metadata={'finish_reason': 'stop'})
    monkeypatch.setattr('heschema.providers.Provider.generate', fake)
    with TestClient(create_app(tmp_path / 'state.sqlite')) as client:
        assert client.post('/contracts', json=contract.as_dict()).status_code == 201
        body = {'contractId': contract.id, 'contractVersion': contract.version,
                'prompt': 'Invoice', 'provider': 'mock', 'promptStyle': 'compact', 'repairs': 1}
        result = client.post('/contracts/generate', json=body).json()
    assert not result['validation']['success'] and not result['executionAuthorized']
    assert result['repair']['requestsAttempted'] == 1
    expected = {'call_tool': 'needs_context', 'ask_clarification': 'ask_clarification', 'refuse': 'refuse'}
    assert result['repair']['stopReason'] == expected[action]
    assert canonical(generation_envelope(contract, contract.schema)) in seen[0][0]['content']
    assert 'Missing required bindings (do not invent): ["/quantity","/unitPriceMinor"]' in seen[0][0]['content']


def test_prompt_style_validation_default_and_context_freshness(tmp_path, monkeypatch):
    monkeypatch.delenv('HESCHEMA_API_TOKEN', raising=False)
    seen = []
    with TestClient(create_app(tmp_path / 'state.sqlite')) as client:
        assert client.post('/contracts', json=INVOICE.as_dict()).status_code == 201
        ctx = client.post('/contexts', json={
            'contractId': INVOICE.id, 'contractVersion': INVOICE.version,
            'data': CTX['data'], 'approvedPointers': CTX['approvedPointers'],
        }).json()
        body = {'contractId': INVOICE.id, 'contractVersion': INVOICE.version,
                'contextId': ctx['id'], 'contextVersion': 1, 'prompt': 'Invoice', 'provider': 'mock'}
        async def fake(self, messages, *args, **kwargs):
            seen.append(messages)
            return Generation(canonical(GOOD), metadata={'finish_reason': 'stop'})
        monkeypatch.setattr('heschema.providers.Provider.generate', fake)
        assert client.post('/contracts/generate', json={**body, 'promptStyle': 'typo'}).status_code == 422
        assert client.post('/contracts/generate', json={**body, 'promptStyle': 'compact'}).status_code == 409
        assert seen == []
        client.post(f"/contexts/{ctx['id']}/confirm", json={'version': 1})
        default = client.post('/contracts/generate', json=body).json()
        explicit = client.post('/contracts/generate', json={**body, 'promptStyle': 'full'}).json()
        assert default['promptStyle'] == explicit['promptStyle'] == 'full'
        assert seen[0] == seen[1]
        async def invalidate(self, messages, *args, **kwargs):
            StateStore(tmp_path / 'state.sqlite').invalidate_context(ctx['id'], 'local-operator', 1)
            return Generation(canonical(GOOD), metadata={'finish_reason': 'stop'})
        monkeypatch.setattr('heschema.providers.Provider.generate', invalidate)
        result = client.post('/contracts/generate', json={**body, 'promptStyle': 'compact', 'repairs': 1}).json()
        assert result['repair']['stopReason'] == 'context_changed'
        assert result['validation']['result'] == 'STALE_CONTEXT'
        assert not result['validation']['accepted']
        assert result['repair']['requestsAttempted'] == 1
