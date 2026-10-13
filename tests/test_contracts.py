import copy
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from heschema.api import create_app
from heschema.context_schema import ContextError, effective_schema
from heschema.contracts import Contract
from heschema.registry import ContractRegistry, builtin_registry
from heschema.schema import SchemaEngine
from heschema.state import StateStore
from heschema.validation import validate_contract

SCHEMA = {'type': 'object', 'properties': {'destination': {'type': 'string'}, 'seats': {'type': 'integer', 'minimum': 1}}, 'required': ['destination', 'seats'], 'additionalProperties': False}
DEFINITION = {'id': 'custom-trip', 'version': '1', 'schema': SCHEMA, 'contextSchema': SCHEMA,
              'bindings': [{'instanceLocation': '/destination', 'contextLocation': '/destination'}]}


def approved(contract, data, pointers):
    return {'id': 'ctx', 'version': 1, 'confirmed': True, 'data': data,
            'approvedPointers': pointers, 'facts': []}


def test_custom_contract_and_partial_approval_do_not_bind_unapproved_fields():
    r = ContractRegistry()
    c = r.register(DEFINITION)
    snap = approved(c, {'destination': 'Goa', 'seats': 2}, ['/destination'])
    engine = SchemaEngine()
    assert validate_contract({'destination': 'Goa', 'seats': 4}, engine, c, snap)['success']
    assert not validate_contract({'destination': 'Pune', 'seats': 4}, engine, c, snap)['success']
    assert not validate_contract({'destination': 'Goa', 'seats': 4}, engine, c)['success']
    c.schema['properties']['destination']['const'] = 'mutated'
    assert r.get(c.id, c.version).schema == SCHEMA
    with pytest.raises(ValueError, match='immutable'):
        r.register({**DEFINITION, 'description': 'changed'})
    assert len(builtin_registry().list()) == 6


def test_nested_array_and_escaped_pointer_projection_preserves_original():
    schema = {'type': 'object', 'properties': {'a/b~c': {'type': 'array', 'items': {'type': 'object', 'properties': {'city': {'type': 'string'}}, 'required': ['city']}}}}
    original = copy.deepcopy(schema)
    c = Contract('nested', '1', schema, bindings=[{'instanceLocation': '/a~1b~0c/0/city', 'contextLocation': '/city'}])
    projected, _ = effective_schema(c, approved(c, {'city': 'Goa'}, ['/city']))
    engine = SchemaEngine()
    assert not engine.errors(projected, {'a/b~c': [{'city': 'Goa'}]})
    assert engine.errors(projected, {'a/b~c': [{'city': 'Pune'}]})
    assert engine.errors(projected, {'a/b~c': []})
    assert schema == original


def test_conflicts_unconfirmed_stale_owner_and_expired_context(tmp_path):
    c = Contract(**DEFINITION)
    with pytest.raises(ContextError, match='Unconfirmed'):
        effective_schema(c, {**approved(c, {}, []), 'confirmed': False})
    conflict = Contract('conflict', '1', {'type': 'object', 'properties': {'x': {'type': 'integer', 'minimum': 3}}}, bindings=[{'instanceLocation': '/x', 'contextLocation': '/x'}])
    with pytest.raises(ContextError, match='contradicts'):
        effective_schema(conflict, approved(conflict, {'x': 1}, ['/x']))
    store = StateStore(tmp_path / 'state.sqlite')
    s = store.create_context('alice', c, {'destination': 'Goa'}, ['/destination'])
    with pytest.raises(KeyError):
        store.get_context(s['id'], 'bob')
    s = store.confirm_context(s['id'], 'alice', 1)
    store.invalidate_context(s['id'], 'alice', 1)
    with pytest.raises(ValueError, match='Stale'):
        store.confirm_context(s['id'], 'alice', 1)
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    with pytest.raises(ContextError, match='expired'):
        store.create_context('alice', c, {}, [], expires_at=past)


def test_api_register_validate_existing_output_and_stale_context(tmp_path, monkeypatch):
    monkeypatch.delenv('HESCHEMA_API_TOKEN', raising=False)
    with TestClient(create_app(tmp_path / 'state.sqlite')) as client:
        assert client.post('/contracts', json=DEFINITION).status_code == 201
        s = client.post('/contexts', json={'contractId': 'custom-trip', 'contractVersion': '1', 'data': {'destination': 'Goa'}, 'approvedPointers': ['/destination']}).json()
        body = {'contractId': 'custom-trip', 'contractVersion': '1', 'output': {'destination': 'Goa', 'seats': 3}, 'contextId': s['id'], 'contextVersion': 1}
        assert client.post('/contracts/validate', json=body).status_code == 409
        assert client.post(f"/contexts/{s['id']}/confirm", json={'version': 1}).status_code == 200
        decision = client.post('/contracts/validate', json=body).json()
        assert decision['result'] == 'PASS' and not decision['executionAuthorized']
        client.post(f"/contexts/{s['id']}/invalidate", json={'version': 1})
        assert client.post('/contracts/validate', json=body).status_code == 409
        assert '/contracts/validate' in client.get('/openapi.json').json()['paths']


def test_partial_context_validation_does_not_rewrite_const_data():
    c = Contract('context-data', '1', {'type': 'object', 'properties': {'payload': True}},
                 contextSchema={'type': 'object', 'properties': {'payload': {'const': {'required': ['x']}}}},
                 bindings=[{'instanceLocation': '/payload', 'contextLocation': '/payload'}])
    with pytest.raises(ContextError, match='Context data violates'):
        effective_schema(c, approved(c, {'payload': {}}, ['/payload']))
    schema, _ = effective_schema(c, approved(c, {'payload': {'required': ['x']}}, ['/payload']))
    assert not SchemaEngine().errors(schema, {'payload': {'required': ['x']}})
