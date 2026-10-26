"""Real PostgreSQL contract checks, including an externally restarted server.

Use a disposable test database. Pass its DSN through HESCHEMA_TEST_POSTGRES_DSN.
The before/after phases exchange contract IDs, never credentials, through a file.
"""
import argparse
import concurrent.futures
import json
import multiprocessing
import os
import time
import uuid
from pathlib import Path

import psycopg

from heschema.registry import ContractRegistry


def definition(identity, description='original'):
    return {'id': identity, 'version': '1', 'schema': {'type': 'object'},
            'description': description}


def worker(identity, description):
    registry = ContractRegistry(os.environ['HESCHEMA_TEST_POSTGRES_DSN'])
    try:
        registry.register(definition(identity, description))
        return 'written'
    except ValueError as exc:
        if 'immutable' not in str(exc):
            raise
        return 'conflict'


def before(path):
    dsn = os.environ['HESCHEMA_TEST_POSTGRES_DSN']
    registry = ContractRegistry(dsn)
    identity = 'registry-test-' + uuid.uuid4().hex
    # Registry predates worker writes, so visibility cannot come from its cache.
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=2, mp_context=multiprocessing.get_context('spawn')
    ) as pool:
        pending = [pool.submit(worker, identity, value) for value in ('first', 'second')]
        outcomes = [job.result(timeout=30) for job in pending]
        assert sorted(outcomes) == ['conflict', 'written'], outcomes
        stored = registry.get(identity, '1').as_dict()
        assert stored['description'] in {'first', 'second'}
        assert pool.submit(worker, identity, stored['description']).result(timeout=30) == 'written'
        other = identity + '-other'
        assert pool.submit(worker, other, 'other').result(timeout=30) == 'written'
    assert {identity, other} <= {c['id'] for c in registry.list()}
    assert ContractRegistry(dsn).get(identity, '1').as_dict() == stored
    path.write_text(json.dumps({'stored': stored, 'other': other}))
    print('PASS: independent processes, conflicting/identical writes, live reads and reconnect')


def after(path):
    dsn = os.environ['HESCHEMA_TEST_POSTGRES_DSN']
    for attempt in range(30):
        try:
            registry = ContractRegistry(dsn)
            break
        except psycopg.OperationalError:
            if attempt == 29:
                raise
            time.sleep(1)
    state = json.loads(path.read_text())
    stored = state['stored']
    assert registry.get(stored['id'], '1').as_dict() == stored
    assert registry.get(state['other'], '1').description == 'other'
    with psycopg.connect(dsn) as conn:
        conn.execute('DELETE FROM contracts WHERE id IN (%s, %s)', (stored['id'], state['other']))
    print('PASS: committed contracts survived real server restart')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['before', 'after'])
    parser.add_argument('state', type=Path)
    args = parser.parse_args()
    (before if args.phase == 'before' else after)(args.state)
