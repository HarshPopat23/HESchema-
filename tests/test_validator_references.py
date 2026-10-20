"""Constructed reference-scope regressions, not measured model responses."""

import copy

import pytest
from fastapi.testclient import TestClient

from heschema.api import create_app
from heschema.context_schema import ContextError
from heschema.contracts import Contract
from heschema.validation import envelope, validate_contract


def snapshot(value):
    return {'id': 'source', 'version': 1, 'confirmed': True, 'data': {'value': value},
            'approvedPointers': ['/value'], 'facts': []}


@pytest.mark.parametrize('kind,reference', [
    ('document', '#/$defs/text'), ('document', '#text'), ('tool_envelope', '#/$defs/text')])
@pytest.mark.parametrize('keyword', ['const', 'enum'])
def test_binding_preflight_preserves_root_definitions_and_anchors(validation_engine, kind, keyword, reference):
    schema = {'type': 'object', '$defs': {'text': {'$anchor': 'text', 'type': 'string', 'minLength': 1}},
              'properties': {'value': {'$ref': reference}, 'other': {'type': 'integer'}},
              'required': ['value', 'other'], 'additionalProperties': False}
    # Envelope support deliberately excludes anchors; use plain definitions there.
    if kind == 'tool_envelope':
        schema['$defs']['text'].pop('$anchor')
    original = copy.deepcopy(schema)
    contract = Contract('references', '1', schema, kind, 'save' if kind == 'tool_envelope' else None,
        bindings=[{'instanceLocation': '/value', 'contextLocation': '/value', 'keyword': keyword}])
    approved = ['alpha', 'beta'] if keyword == 'enum' else 'alpha'
    for value in (['alpha', 'beta'] if keyword == 'enum' else ['alpha']):
        doc = {'value': value, 'other': 7}
        raw = envelope('call_tool', 'save', doc) if kind == 'tool_envelope' else doc
        result = validate_contract(raw, validation_engine, contract, snapshot(approved))
        assert result['accepted'] and result['success']
    bad = {'value': 'outside-approved-set', 'other': 7}
    raw = envelope('call_tool', 'save', bad) if kind == 'tool_envelope' else bad
    assert not validate_contract(raw, validation_engine, contract, snapshot(approved))['accepted']
    with pytest.raises(ContextError, match='contradicts'):
        validate_contract(raw, validation_engine, contract, snapshot([''] if keyword == 'enum' else ''))
    assert schema == original


def test_nested_resource_reference_uses_ancestor_id_scope(validation_engine):
    schema = {'$id': 'https://example.test/root', 'type': 'object',
        '$defs': {'text': {'type': 'integer'}},
        'properties': {'package': {'$id': 'child', 'type': 'object',
            '$defs': {'text': {'type': 'string', 'minLength': 1}},
            'properties': {'value': {'$ref': '#/$defs/text'}}, 'required': ['value']}},
        'required': ['package']}
    contract = Contract('nested-resource', '1', schema, bindings=[
        {'instanceLocation': '/package/value', 'contextLocation': '/value'}])
    result = validate_contract({'package': {'value': 'alpha'}}, validation_engine, contract, snapshot('alpha'))
    assert result['accepted'] and result['success']
    with pytest.raises(ContextError, match='contradicts'):
        validate_contract({'package': {'value': 2}}, validation_engine, contract, snapshot(2))


@pytest.mark.parametrize('name', ['a/b~c', 'a#?% é'])
def test_preflight_schema_pointer_escapes_fragment_and_property_names(validation_engine, name):
    from heschema.diagnostics import pointer
    schema = {'type': 'object', '$defs': {'text': {'type': 'string'}},
              'properties': {name: {'$ref': '#/$defs/text'}}}
    contract = Contract('escaped', '1', schema, bindings=[
        {'instanceLocation': pointer([name]), 'contextLocation': '/value'}])
    assert validate_contract({name: 'alpha'}, validation_engine, contract, snapshot('alpha'))['success']


def test_api_accepts_referenced_enum_alternatives_after_context_confirmation(tmp_path, monkeypatch, validation_engine):
    monkeypatch.setenv('HESCHEMA_API_TOKEN', '')
    monkeypatch.setenv('HESCHEMA_ENGINE', validation_engine.backend)
    contract = Contract('api-ref-control', '1', {'type': 'object',
        '$defs': {'text': {'type': 'string', 'minLength': 1}},
        'properties': {'value': {'$ref': '#/$defs/text'}}},
        bindings=[{'instanceLocation': '/value', 'contextLocation': '/value', 'keyword': 'enum'}])
    with TestClient(create_app(tmp_path / 'state.sqlite')) as client:
        assert client.post('/contracts', json=contract.as_dict()).status_code == 201
        created = client.post('/contexts', json={'contractId': contract.id, 'contractVersion': '1',
            'data': {'value': ['alpha', 'beta']}, 'approvedPointers': ['/value']})
        assert created.status_code == 201
        context = created.json()
        assert client.post(f"/contexts/{context['id']}/confirm", json={'version': 1}).status_code == 200
        for value in ['alpha', 'beta']:
            result = client.post('/contracts/validate', json={'contractId': contract.id, 'contractVersion': '1',
                'contextId': context['id'], 'contextVersion': 1, 'output': {'value': value}})
            assert result.status_code == 200 and result.json()['success']


def test_api_explicit_null_is_distinct_from_omitted_output(tmp_path, monkeypatch):
    monkeypatch.setenv('HESCHEMA_API_TOKEN', '')
    with TestClient(create_app(tmp_path / 'state.sqlite')) as client:
        contract = Contract('null-api-control', '1', {'type': 'null'})
        assert client.post('/contracts', json=contract.as_dict()).status_code == 201
        body = {'contractId': contract.id, 'contractVersion': '1'}
        explicit = client.post('/contracts/validate', json={**body, 'output': None}).json()
        missing = client.post('/contracts/validate', json=body).json()
        assert explicit['accepted'] and explicit['result'] == 'NOT_CHECKED'
        assert not missing['accepted'] and missing['result'] == 'NOT_EVALUATED'
