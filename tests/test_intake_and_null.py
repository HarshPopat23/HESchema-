from fastapi.testclient import TestClient

from heschema.api import create_app
from heschema.jsonio import read_json
from heschema.providers import ROOT
from heschema.schema import SchemaEngine, check_schema


def test_use_case_record_and_examples_conform_and_survive_registration_restart(tmp_path, monkeypatch):
    monkeypatch.delenv('HESCHEMA_API_TOKEN', raising=False)
    engine = SchemaEngine()
    schema = read_json(ROOT / 'docs/use-case-record.schema.json')
    for path in (ROOT / 'docs/use-cases').glob('*.json'):
        record = read_json(path)
        assert not engine.errors(schema, record)
        assert record['provenance'] == 'author_created_synthetic'
    db = tmp_path / 'state.sqlite'
    with TestClient(create_app(db)) as client:
        for name in ('invoice', 'trip'):
            example = client.get('/ui/contracts/examples/' + name).json()
            assert client.post('/contracts', json=example['contract']).status_code == 201
        assert client.post('/contracts', json={'id': 'null-document', 'version': '1', 'schema': {'type': 'null'}}).status_code == 201
        body = {'contractId': 'null-document', 'contractVersion': '1'}
        absent = client.post('/contracts/validate', json=body).json()
        explicit_null = client.post('/contracts/validate', json={**body, 'output': None}).json()
        assert absent['stages']['json'] == 'not_evaluated'
        assert explicit_null['stages']['originalSchema'] == 'valid'
        assert not explicit_null['success']
    with TestClient(create_app(db)) as client:
        assert client.get('/contracts/invoice-demo/1').status_code == 200
        assert client.get('/contracts/trip-demo/1').status_code == 200


def test_unknown_required_vocabulary_cannot_be_silently_ignored():
    import pytest
    with pytest.raises(ValueError, match='Required custom vocabulary'):
        check_schema({'$vocabulary': {'https://example.test/vocab': True}})
    check_schema({'$vocabulary': {'https://example.test/vocab': False}})
