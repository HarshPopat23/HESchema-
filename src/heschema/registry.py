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
        if self.path:
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
                with sqlite3.connect(self.path) as db:
                    db.execute('INSERT OR IGNORE INTO contracts VALUES (?, ?, ?)', (*key, canonical(data)))
                    stored = db.execute('SELECT definition FROM contracts WHERE id=? AND version=?', key).fetchone()[0]
                    if stored != canonical(data):
                        raise ValueError('An existing contract version is immutable; use a new version')
            self._definitions[key] = copy.deepcopy(data)
        return self.get(*key)

    def get(self, contract_id, version):
        with self._lock:
            try:
                return Contract(**copy.deepcopy(self._definitions[(contract_id, version)]))
            except KeyError:
                raise KeyError('Unknown contract/version') from None

    def list(self):
        with self._lock:
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
