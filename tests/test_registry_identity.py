"""Immutable definitions retain JSON types; persistent reads see committed writes."""
import multiprocessing
from unittest.mock import MagicMock

import psycopg
import pytest

from heschema import Contract
from heschema.jsonio import canonical
from heschema.registry import ContractRegistry

PAIRS = [(True, 1), (False, 0), ({'flag': True}, {'flag': 1}),
         ([False], [0]), (1, 1.0)]


def definition(value, identity='typed'):
    return Contract(identity, '1', {'const': value})


@pytest.mark.parametrize('backend', ['memory', 'sqlite', 'postgres'])
@pytest.mark.parametrize('original,replacement', PAIRS)
def test_registry_rejects_type_distinct_definition(tmp_path, monkeypatch, backend,
                                                  original, replacement):
    first = definition(original)
    if backend == 'postgres':
        connection = MagicMock()
        connection.__enter__.return_value = connection
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = []
        cursor.fetchone.return_value = (canonical(first.as_dict()),)
        monkeypatch.setattr(psycopg, 'connect', MagicMock(return_value=connection))
        registry = ContractRegistry('postgresql://test')
    else:
        registry = ContractRegistry(tmp_path / 'contracts.db' if backend == 'sqlite' else None)
    registry.register(first)
    with pytest.raises(ValueError, match='immutable'):
        registry.register(definition(replacement))
    assert canonical(registry.get('typed', '1').as_dict()) == canonical(first.as_dict())


@pytest.mark.parametrize('persistent', [False, True])
def test_identical_definition_and_reordered_keys_are_idempotent(tmp_path, persistent):
    registry = ContractRegistry(tmp_path / 'contracts.db' if persistent else None)
    first = Contract('same', '1', {'type': 'object', 'const': {'a': True, 'b': 1}})
    second = Contract('same', '1', {'const': {'b': 1, 'a': True}, 'type': 'object'})
    registry.register(first)
    registry.register(second)
    assert canonical(registry.get('same', '1').as_dict()) == canonical(first.as_dict())


def test_sqlite_existing_instances_see_get_and_list_changes(tmp_path):
    path = tmp_path / 'contracts.db'
    writer, reader = ContractRegistry(path), ContractRegistry(path)
    with pytest.raises(KeyError, match='Unknown contract'):
        reader.get('typed', '1')
    assert reader.list() == []
    writer.register(definition(True))
    assert reader.get('typed', '1').schema['const'] is True
    assert [item['id'] for item in reader.list()] == ['typed']
    # Return values cannot mutate persisted definitions.
    reader.get('typed', '1').schema['const'] = False
    reader.list()[0]['schema']['const'] = False
    assert reader.get('typed', '1').schema['const'] is True


def register_worker(path, value, barrier, outcomes):
    registry = ContractRegistry(path)
    barrier.wait(timeout=20)
    try:
        registry.register(definition(value))
        outcomes.put('written')
    except ValueError as exc:
        if 'immutable' not in str(exc):
            raise
        outcomes.put('conflict')


@pytest.mark.parametrize('left,right,expected', [
    (True, 1, ['conflict', 'written']),
    (False, 0, ['conflict', 'written']),
    ({'flag': True}, {'flag': 1}, ['conflict', 'written']),
    (1, 1.0, ['conflict', 'written']),
    ({'flag': True}, {'flag': True}, ['written', 'written']),
])
def test_sqlite_process_conflicts_and_live_reads(tmp_path, left, right, expected):
    path = str(tmp_path / 'contracts.db')
    reader = ContractRegistry(path)
    context = multiprocessing.get_context('spawn')
    barrier, outcomes = context.Barrier(2), context.Queue()
    processes = [context.Process(target=register_worker, args=(path, value, barrier, outcomes))
                 for value in (left, right)]
    try:
        for process in processes:
            process.start()
        actual = [outcomes.get(timeout=30) for _ in processes]
        for process in processes:
            process.join(timeout=10)
            assert process.exitcode == 0
        assert sorted(actual) == expected
        stored = reader.get('typed', '1')
        assert canonical(stored.schema['const']) in {canonical(left), canonical(right)}
        assert canonical(reader.list()[0]) == canonical(stored.as_dict())
        assert canonical(ContractRegistry(path).get('typed', '1').as_dict()) == canonical(stored.as_dict())
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=10)
        outcomes.close()
        outcomes.join_thread()


@pytest.mark.parametrize('operation', ['get', 'list'])
def test_sqlite_read_failure_does_not_return_cached_definition(tmp_path, operation):
    import sqlite3

    path = tmp_path / 'contracts.db'
    registry = ContractRegistry(path)
    registry.register(definition(True))
    with sqlite3.connect(path) as db:
        db.execute('DROP TABLE contracts')
    with pytest.raises(sqlite3.OperationalError):
        registry.get('typed', '1') if operation == 'get' else registry.list()


def test_sqlite_identity_ignores_stored_json_formatting(tmp_path):
    import json
    import sqlite3

    path = tmp_path / 'contracts.db'
    registry = ContractRegistry(path)
    original = definition({'flag': True, 'number': 1})
    registry.register(original)
    with sqlite3.connect(path) as db:
        db.execute('UPDATE contracts SET definition=?',
                   (json.dumps(original.as_dict(), indent=2, sort_keys=False),))
    registry.register(original)
    assert canonical(registry.get('typed', '1').as_dict()) == canonical(original.as_dict())
