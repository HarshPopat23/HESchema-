"""The API token authenticates one shared operator, never tenant headers."""
import pytest
from fastapi.testclient import TestClient

from heschema.api import create_app
from heschema.state import StateStore


@pytest.mark.parametrize('token,identity', [('shared-test-only', 'operator'), ('', 'local-operator')])
def test_clients_share_operator_and_cannot_choose_tenant(tmp_path, monkeypatch, token, identity):
    monkeypatch.setenv('HESCHEMA_API_TOKEN', token)
    database = tmp_path / 'state.sqlite'
    authorization = {'Authorization': 'Bearer ' + token} if token else {}
    with TestClient(create_app(database)) as client:
        first = {**authorization, 'X-Tenant-ID': 'alice', 'X-User-ID': 'alice'}
        second = {**authorization, 'X-Tenant-ID': 'bob', 'X-User-ID': 'bob'}
        response = client.post('/states', headers=first, json={'prompt': 'boundary', 'state': {'x': 1}})
        assert response.status_code == 200
        state_id = response.json()['id']
        assert client.get('/states/' + state_id, headers=second).status_code == 200
        assert StateStore(database).get(state_id, identity)['id'] == state_id
        with pytest.raises(KeyError):
            StateStore(database).get(state_id, 'alice')
        schema = client.get('/openapi.json').json()
        assert 'Single-operator' in schema['info']['description']
        assert 'single backend operator' in schema['components']['securitySchemes']['HTTPBearer']['description']
        if token:
            for headers in ({}, {'Authorization': 'Bearer invalid', 'X-Tenant-ID': 'operator'}):
                assert client.get('/states/' + state_id, headers=headers).status_code == 401
                assert client.post('/v1/chat/completions', headers=headers, json={}).status_code == 401
        assert client.get('/health').status_code == 200
