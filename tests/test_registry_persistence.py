"""Fail-closed database boundaries, including failures during transaction commit."""
from unittest.mock import MagicMock

import psycopg
import pytest

from heschema.registry import ContractRegistry

DEFINITION = {'id': 'persistence-test', 'version': '1', 'schema': {'type': 'object'}}


@pytest.mark.parametrize('phase', ['connect', 'write', 'commit', 'missing-row'])
def test_postgres_registration_does_not_cache_failed_writes(monkeypatch, phase):
    connection = MagicMock()
    connection.__enter__.return_value = connection
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = []
    connect = MagicMock(return_value=connection)
    monkeypatch.setattr(psycopg, 'connect', connect)
    registry = ContractRegistry('postgresql://test')
    if phase == 'connect':
        connect.side_effect = psycopg.OperationalError('unavailable')
    elif phase == 'write':
        cursor.execute.side_effect = psycopg.OperationalError('write failed')
    elif phase == 'commit':
        from heschema.contracts import Contract
        from heschema.jsonio import canonical
        cursor.fetchone.return_value = (canonical(Contract(**DEFINITION).as_dict()),)
        connection.__exit__.side_effect = psycopg.OperationalError('commit failed')
    else:
        cursor.fetchone.return_value = None
    with pytest.raises((psycopg.OperationalError, RuntimeError)):
        registry.register(DEFINITION)
    assert registry._definitions == {}


def test_postgres_initialization_failure_is_visible(monkeypatch):
    def fail(*args, **kwargs):
        raise psycopg.OperationalError('unavailable')
    monkeypatch.setattr(psycopg, 'connect', fail)
    with pytest.raises(psycopg.OperationalError, match='unavailable'):
        ContractRegistry('postgresql://test')


@pytest.mark.parametrize('operation', ['get', 'list'])
def test_postgres_reads_do_not_fall_back_to_stale_cache(monkeypatch, operation):
    connection = MagicMock()
    connection.__enter__.return_value = connection
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = []
    connect = MagicMock(return_value=connection)
    monkeypatch.setattr(psycopg, 'connect', connect)
    registry = ContractRegistry('postgresql://test')
    registry._definitions[('persistence-test', '1')] = DEFINITION
    connect.side_effect = psycopg.OperationalError('unavailable')
    with pytest.raises(psycopg.OperationalError, match='unavailable'):
        if operation == 'get':
            registry.get('persistence-test', '1')
        else:
            registry.list()
