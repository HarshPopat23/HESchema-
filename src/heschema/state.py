"""SQLite state snapshots with explicit confirmation, ownership and version checks."""

import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .jsonio import canonical, loads


class StateStore:
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS states (
                id TEXT PRIMARY KEY, owner TEXT NOT NULL, version INTEGER NOT NULL,
                prompt TEXT NOT NULL, payload TEXT NOT NULL, confirmed INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @contextmanager
    def transaction(self, mode="IMMEDIATE"):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute(f"BEGIN {mode}")
        try:
            yield db
            db.execute("COMMIT")
        except Exception:
            db.execute("ROLLBACK")
            raise
        finally:
            db.close()

    def create(self, owner, prompt, state):
        state_id = secrets.token_urlsafe(24)
        with self.connect() as db:
            db.execute("INSERT INTO states(id,owner,version,prompt,payload,confirmed) VALUES(?,?,1,?,?,0)",
                       (state_id, owner, prompt, canonical(state)))
        return self.get(state_id, owner)

    def get(self, state_id, owner):
        with self.connect() as db:
            row = db.execute("SELECT * FROM states WHERE id=? AND owner=?", (state_id, owner)).fetchone()
        if row is None:
            raise KeyError("State not found")
        result = dict(row)
        result["state"] = loads(result.pop("payload"))
        result["confirmed"] = bool(result["confirmed"])
        return result

    def confirm(self, state_id, owner, version):
        with self.transaction("IMMEDIATE") as db:
            cursor = db.execute("UPDATE states SET confirmed=1 WHERE id=? AND owner=? AND version=?",
                                (state_id, owner, version))
            if cursor.rowcount != 1:
                raise ValueError("State ownership/version mismatch")
            row = db.execute("SELECT * FROM states WHERE id=? AND owner=?", (state_id, owner)).fetchone()
            if row is None:
                raise KeyError("State not found")
            result = dict(row)
            result["state"] = loads(result.pop("payload"))
            result["confirmed"] = bool(result["confirmed"])
            return result

    def replace(self, state_id, owner, version, state):
        with self.transaction("IMMEDIATE") as db:
            cursor = db.execute("UPDATE states SET payload=?,version=version+1,confirmed=0 WHERE id=? AND owner=? AND version=?",
                                (canonical(state), state_id, owner, version))
            if cursor.rowcount != 1:
                raise ValueError("Stale state or unknown owner")
            row = db.execute("SELECT * FROM states WHERE id=? AND owner=?", (state_id, owner)).fetchone()
            if row is None:
                raise KeyError("State not found")
            result = dict(row)
            result["state"] = loads(result.pop("payload"))
            result["confirmed"] = bool(result["confirmed"])
            return result

    def create_context(self, owner, contract, data, approved_pointers, facts=None, expires_at=None):
        from datetime import datetime, timezone

        from .context_schema import ContextError, check_context, effective_schema
        from .diagnostics import resolve
        for location in approved_pointers:
            resolve(data, location)
        if expires_at and datetime.fromisoformat(expires_at).tzinfo is None:
            raise ContextError('Approval expiry requires a timezone')
        facts = facts or []
        for fact in facts:
            if set(fact) != {'contextLocation', 'source', 'version', 'verified', 'expiresAt'}:
                raise ContextError('Fact requires contextLocation, source, version, verified and expiresAt')
            resolve(data, fact['contextLocation'])
            if fact['verified'] is not True or datetime.fromisoformat(fact['expiresAt']).tzinfo is None:
                raise ContextError('Fact verification and timezone-aware expiry required')
        context_id = secrets.token_urlsafe(24)
        payload = {'contractId': contract.id, 'contractVersion': contract.version,
                   'contractHash': contract.identity['hash'], 'data': data,
                   'approvedPointers': list(dict.fromkeys(approved_pointers)), 'facts': facts,
                   'expiresAt': expires_at, 'createdAt': datetime.now(timezone.utc).isoformat()}
        check_context({'id': context_id, 'version': 1, 'confirmed': True, **payload})
        effective_schema(contract, {'id': context_id, 'version': 1, 'confirmed': True, **payload})
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS contexts (id TEXT PRIMARY KEY, owner TEXT NOT NULL, version INTEGER NOT NULL, confirmed INTEGER NOT NULL, payload TEXT NOT NULL)')
            db.execute('INSERT INTO contexts VALUES (?, ?, 1, 0, ?)', (context_id, owner, canonical(payload)))
        return self.get_context(context_id, owner)

    def get_context(self, context_id, owner):
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS contexts (id TEXT PRIMARY KEY, owner TEXT NOT NULL, version INTEGER NOT NULL, confirmed INTEGER NOT NULL, payload TEXT NOT NULL)')
            row = db.execute('SELECT * FROM contexts WHERE id=? AND owner=?', (context_id, owner)).fetchone()
        if row is None:
            raise KeyError('Context not found')
        return {'id': row['id'], 'version': row['version'], 'confirmed': bool(row['confirmed']), **loads(row['payload'])}

    def confirm_context(self, context_id, owner, version):
        from .context_schema import check_context
        with self.transaction("IMMEDIATE") as db:
            db.execute('CREATE TABLE IF NOT EXISTS contexts (id TEXT PRIMARY KEY, owner TEXT NOT NULL, version INTEGER NOT NULL, confirmed INTEGER NOT NULL, payload TEXT NOT NULL)')
            row = db.execute('SELECT * FROM contexts WHERE id=? AND owner=?', (context_id, owner)).fetchone()
            if row is None:
                raise KeyError('Context not found')
            proposed = {'id': row['id'], 'version': row['version'], 'confirmed': bool(row['confirmed']), **loads(row['payload'])}
            check_context({**proposed, 'confirmed': True}, version=version)
            cursor = db.execute('UPDATE contexts SET confirmed=1 WHERE id=? AND owner=? AND version=?', (context_id, owner, version))
            if cursor.rowcount != 1:
                raise ValueError('Stale context version')
            row = db.execute('SELECT * FROM contexts WHERE id=? AND owner=?', (context_id, owner)).fetchone()
            return {'id': row['id'], 'version': row['version'], 'confirmed': bool(row['confirmed']), **loads(row['payload'])}

    def invalidate_context(self, context_id, owner, version):
        with self.transaction("IMMEDIATE") as db:
            db.execute('CREATE TABLE IF NOT EXISTS contexts (id TEXT PRIMARY KEY, owner TEXT NOT NULL, version INTEGER NOT NULL, confirmed INTEGER NOT NULL, payload TEXT NOT NULL)')
            cursor = db.execute('UPDATE contexts SET confirmed=0, version=version+1 WHERE id=? AND owner=? AND version=?', (context_id, owner, version))
            if cursor.rowcount != 1:
                raise ValueError('Stale context version')
            row = db.execute('SELECT * FROM contexts WHERE id=? AND owner=?', (context_id, owner)).fetchone()
            if row is None:
                raise KeyError('Context not found')
            return {'id': row['id'], 'version': row['version'], 'confirmed': bool(row['confirmed']), **loads(row['payload'])}
