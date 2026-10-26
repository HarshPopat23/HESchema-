"""Local contract registration; third parties do not modify the built-in domain table."""

import copy
import sqlite3
import threading

from .contracts import Contract
from .domains import DOMAINS, reference_schema
from .jsonio import canonical, loads


class ContractRegistry:
    def __init__(self, path=None):
        self._definitions = {}
        self._lock = threading.RLock()
        self.path = str(path) if path else None
        self._is_postgres = bool(self.path and (self.path.startswith("postgres://") or self.path.startswith("postgresql://")))
        if self.path:
            if self._is_postgres:
                import psycopg
                with psycopg.connect(self.path) as conn:
                    with conn.cursor() as cur:
                        cur.execute('CREATE TABLE IF NOT EXISTS contracts (id VARCHAR(255), version VARCHAR(64), definition TEXT NOT NULL, PRIMARY KEY (id, version))')
                        cur.execute('SELECT id, version, definition FROM contracts')
                        for contract_id, version, raw in cur.fetchall():
                            data = loads(raw)
                            Contract(**data)
                            self._definitions[(contract_id, version)] = data
            else:
                with sqlite3.connect(self.path) as db:
                    db.execute('CREATE TABLE IF NOT EXISTS contracts (id TEXT, version TEXT, definition TEXT NOT NULL, PRIMARY KEY (id, version))')
                    for contract_id, version, raw in db.execute('SELECT id, version, definition FROM contracts'):
                        data = loads(raw)
                        Contract(**data)
                        self._definitions[(contract_id, version)] = data

    def register(self, definition):
        contract = definition if isinstance(definition, Contract) else Contract(**definition)
        key, data = (contract.id, contract.version), contract.as_dict()
        with self._lock:
            if key in self._definitions and self._definitions[key] != data:
                raise ValueError('An existing contract version is immutable; use a new version')
            if self.path:
                if self._is_postgres:
                    import psycopg
                    # The connection context commits before the cache is updated.
                    # Connection, write and commit failures must reach the caller.
                    with psycopg.connect(self.path) as conn:
                        with conn.cursor() as cur:
                            cur.execute('INSERT INTO contracts VALUES (%s, %s, %s) ON CONFLICT (id, version) DO NOTHING', (*key, canonical(data)))
                            cur.execute('SELECT definition FROM contracts WHERE id=%s AND version=%s', key)
                            row = cur.fetchone()
                            if row is None:
                                raise RuntimeError('Contract write was not persisted')
                            if canonical(loads(row[0])) != canonical(data):
                                raise ValueError('An existing contract version is immutable; use a new version')
                else:
                    with sqlite3.connect(self.path) as db:
                        db.execute('INSERT OR IGNORE INTO contracts VALUES (?, ?, ?)', (*key, canonical(data)))
                        stored = db.execute('SELECT definition FROM contracts WHERE id=? AND version=?', key).fetchone()[0]
                        if stored != canonical(data):
                            raise ValueError('An existing contract version is immutable; use a new version')
            self._definitions[key] = copy.deepcopy(data)
        return self.get(*key)

    def get(self, contract_id, version):
        with self._lock:
            if self._is_postgres:
                import psycopg
                with psycopg.connect(self.path) as conn:
                    with conn.cursor() as cur:
                        cur.execute('SELECT definition FROM contracts WHERE id=%s AND version=%s', (contract_id, version))
                        row = cur.fetchone()
                if row is None:
                    raise KeyError('Unknown contract/version')
                return Contract(**loads(row[0]))
            try:
                return Contract(**copy.deepcopy(self._definitions[(contract_id, version)]))
            except KeyError:
                raise KeyError('Unknown contract/version') from None

    def list(self):
        with self._lock:
            if self._is_postgres:
                import psycopg
                with psycopg.connect(self.path) as conn:
                    with conn.cursor() as cur:
                        cur.execute('SELECT definition FROM contracts ORDER BY id, version')
                        return [Contract(**loads(row[0])).as_dict() for row in cur.fetchall()]
            return [self.get(*key).as_dict() for key in sorted(self._definitions)]


def builtin_registry(path=None):
    result = ContractRegistry(path)
    for domain, spec in DOMAINS.items():
        schema = reference_schema(domain)
        relationships = [{'id': f'order-{a}-{b}', 'kind': 'date_before', 'left': '/' + a, 'right': '/' + b}
                         for a, b in spec.get('policy', {}).get('ordered', [])]
        result.register(Contract(domain, '1', schema, 'tool_envelope', spec['tool'], spec['description'],
                                 schema, [{'instanceLocation': '/' + key, 'contextLocation': '/' + key}
                                          for key in schema.get('required', [])], relationships))
    return result
