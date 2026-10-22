"""State snapshots with explicit confirmation, ownership and version checks.
Supports pluggable storage backends: SQLite (single-node WAL) and PostgreSQL (distributed multi-pod).
"""

import abc
import os
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional

from .jsonio import canonical, loads


class BaseStateStore(abc.ABC):
    """Abstract base state store ensuring consistent optimistic locking and context guarantees."""

    @abc.abstractmethod
    def create(self, owner: str, prompt: str, state: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    def get(self, state_id: str, owner: str) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    def confirm(self, state_id: str, owner: str, version: int) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    def replace(self, state_id: str, owner: str, version: int, state: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    def create_context(self, owner: str, contract: Any, data: Dict[str, Any], approved_pointers: list, facts: Optional[list] = None, expires_at: Optional[str] = None) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    def get_context(self, context_id: str, owner: str) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    def confirm_context(self, context_id: str, owner: str, version: int) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    def invalidate_context(self, context_id: str, owner: str, version: int) -> Dict[str, Any]:
        pass


class StateStore(BaseStateStore):
    """Factory and interface for state stores; dynamically routes between SQLite and PostgreSQL."""

    def __new__(cls, path_or_uri: Any):
        uri_str = str(path_or_uri)
        if uri_str.startswith("postgresql://") or uri_str.startswith("postgres://"):
            return super().__new__(PostgresStateStore)
        return super().__new__(SQLiteStateStore)


class SQLiteStateStore(StateStore):
    """High-performance SQLite backend configured with Write-Ahead Logging (WAL) and busy timeout."""

    def __init__(self, path: Any):
        uri_str = str(path)
        if uri_str.startswith("sqlite:///"):
            uri_str = uri_str.replace("sqlite:///", "")
        p = Path(uri_str)
        p.parent.mkdir(parents=True, exist_ok=True)
        self.path = str(p)
        with self.connect() as db:
            db.execute("PRAGMA journal_mode = WAL")
            db.execute("PRAGMA synchronous = NORMAL")
            db.execute("PRAGMA busy_timeout = 5000")
            db.execute("""CREATE TABLE IF NOT EXISTS states (
                id TEXT PRIMARY KEY, owner TEXT NOT NULL, version INTEGER NOT NULL,
                prompt TEXT NOT NULL, payload TEXT NOT NULL, confirmed INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            db.execute("""CREATE TABLE IF NOT EXISTS contexts (
                id TEXT PRIMARY KEY, owner TEXT NOT NULL, version INTEGER NOT NULL,
                confirmed INTEGER NOT NULL, payload TEXT NOT NULL)""")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout = 5000")
        try:
            with db:
                yield db
        finally:
            db.close()

    @contextmanager
    def transaction(self, mode: str = "IMMEDIATE"):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout = 5000")
        db.execute(f"BEGIN {mode}")
        try:
            yield db
            db.execute("COMMIT")
        except Exception:
            db.execute("ROLLBACK")
            raise
        finally:
            db.close()

    def create(self, owner: str, prompt: str, state: Dict[str, Any]) -> Dict[str, Any]:
        state_id = secrets.token_urlsafe(24)
        with self.connect() as db:
            db.execute("INSERT INTO states(id,owner,version,prompt,payload,confirmed) VALUES(?,?,1,?,?,0)",
                       (state_id, owner, prompt, canonical(state)))
        return self.get(state_id, owner)

    def get(self, state_id: str, owner: str) -> Dict[str, Any]:
        with self.connect() as db:
            row = db.execute("SELECT * FROM states WHERE id=? AND owner=?", (state_id, owner)).fetchone()
        if row is None:
            raise KeyError("State not found")
        result = dict(row)
        result["state"] = loads(result.pop("payload"))
        result["confirmed"] = bool(result["confirmed"])
        return result

    def confirm(self, state_id: str, owner: str, version: int) -> Dict[str, Any]:
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

    def replace(self, state_id: str, owner: str, version: int, state: Dict[str, Any]) -> Dict[str, Any]:
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

    def create_context(self, owner: str, contract: Any, data: Dict[str, Any], approved_pointers: list, facts: Optional[list] = None, expires_at: Optional[str] = None) -> Dict[str, Any]:
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

    def get_context(self, context_id: str, owner: str) -> Dict[str, Any]:
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS contexts (id TEXT PRIMARY KEY, owner TEXT NOT NULL, version INTEGER NOT NULL, confirmed INTEGER NOT NULL, payload TEXT NOT NULL)')
            row = db.execute('SELECT * FROM contexts WHERE id=? AND owner=?', (context_id, owner)).fetchone()
        if row is None:
            raise KeyError('Context not found')
        return {'id': row['id'], 'version': row['version'], 'confirmed': bool(row['confirmed']), **loads(row['payload'])}

    def confirm_context(self, context_id: str, owner: str, version: int) -> Dict[str, Any]:
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

    def invalidate_context(self, context_id: str, owner: str, version: int) -> Dict[str, Any]:
        with self.transaction("IMMEDIATE") as db:
            db.execute('CREATE TABLE IF NOT EXISTS contexts (id TEXT PRIMARY KEY, owner TEXT NOT NULL, version INTEGER NOT NULL, confirmed INTEGER NOT NULL, payload TEXT NOT NULL)')
            cursor = db.execute('UPDATE contexts SET confirmed=0, version=version+1 WHERE id=? AND owner=? AND version=?', (context_id, owner, version))
            if cursor.rowcount != 1:
                raise ValueError('Stale context version')
            row = db.execute('SELECT * FROM contexts WHERE id=? AND owner=?', (context_id, owner)).fetchone()
            if row is None:
                raise KeyError('Context not found')
            return {'id': row['id'], 'version': row['version'], 'confirmed': bool(row['confirmed']), **loads(row['payload'])}


class PostgresStateStore(StateStore):
    """Horizontally scalable PostgreSQL backend for distributed Kubernetes pods and serverless containers."""

    def __init__(self, uri: str):
        self.uri = str(uri)
        self.path = self.uri
        self._initialized = False

    def _ensure_tables(self):
        if self._initialized:
            return
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""CREATE TABLE IF NOT EXISTS states (
                    id VARCHAR(64) PRIMARY KEY,
                    owner VARCHAR(255) NOT NULL,
                    version INTEGER NOT NULL,
                    prompt TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    confirmed BOOLEAN NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
                cur.execute("""CREATE TABLE IF NOT EXISTS contexts (
                    id VARCHAR(64) PRIMARY KEY,
                    owner VARCHAR(255) NOT NULL,
                    version INTEGER NOT NULL,
                    confirmed BOOLEAN NOT NULL,
                    payload TEXT NOT NULL)""")
        self._initialized = True

    @contextmanager
    def connect(self):
        try:
            import psycopg
        except ImportError:
            raise RuntimeError("PostgreSQL backend requires psycopg: pip install 'psycopg[binary]'") from None
        conn = psycopg.connect(self.uri)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    @contextmanager
    def cursor(self):
        self._ensure_tables()
        try:
            from psycopg.rows import dict_row
        except ImportError:
            dict_row = None
        with self.connect() as conn:
            try:
                cur = conn.cursor(row_factory=dict_row)
            except TypeError:
                cur = conn.cursor()
            try:
                yield cur
            finally:
                cur.close()

    def create(self, owner: str, prompt: str, state: Dict[str, Any]) -> Dict[str, Any]:
        state_id = secrets.token_urlsafe(24)
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO states(id, owner, version, prompt, payload, confirmed) VALUES (%s, %s, %s, %s, %s, %s)",
                (state_id, owner, 1, prompt, canonical(state), False),
            )
        return self.get(state_id, owner)

    def get(self, state_id: str, owner: str) -> Dict[str, Any]:
        with self.cursor() as cur:
            cur.execute("SELECT * FROM states WHERE id=%s AND owner=%s", (state_id, owner))
            row = cur.fetchone()
        if row is None:
            raise KeyError("State not found")
        result = dict(row)
        result["state"] = loads(result.pop("payload"))
        result["confirmed"] = bool(result["confirmed"])
        return result

    def confirm(self, state_id: str, owner: str, version: int) -> Dict[str, Any]:
        with self.cursor() as cur:
            cur.execute(
                "UPDATE states SET confirmed=TRUE WHERE id=%s AND owner=%s AND version=%s",
                (state_id, owner, version),
            )
            if cur.rowcount != 1:
                raise ValueError("State ownership/version mismatch")
        return self.get(state_id, owner)

    def replace(self, state_id: str, owner: str, version: int, state: Dict[str, Any]) -> Dict[str, Any]:
        with self.cursor() as cur:
            cur.execute(
                "UPDATE states SET payload=%s, version=version+1, confirmed=FALSE WHERE id=%s AND owner=%s AND version=%s",
                (canonical(state), state_id, owner, version),
            )
            if cur.rowcount != 1:
                raise ValueError("Stale state or unknown owner")
        return self.get(state_id, owner)

    def create_context(self, owner: str, contract: Any, data: Dict[str, Any], approved_pointers: list, facts: Optional[list] = None, expires_at: Optional[str] = None) -> Dict[str, Any]:
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
        with self.cursor() as cur:
            cur.execute("INSERT INTO contexts (id, owner, version, confirmed, payload) VALUES (%s, %s, 1, FALSE, %s)",
                        (context_id, owner, canonical(payload)))
        return self.get_context(context_id, owner)

    def get_context(self, context_id: str, owner: str) -> Dict[str, Any]:
        with self.cursor() as cur:
            cur.execute("SELECT * FROM contexts WHERE id=%s AND owner=%s", (context_id, owner))
            row = cur.fetchone()
        if row is None:
            raise KeyError('Context not found')
        result = dict(row)
        return {'id': result['id'], 'version': result['version'], 'confirmed': bool(result['confirmed']), **loads(result['payload'])}

    def confirm_context(self, context_id: str, owner: str, version: int) -> Dict[str, Any]:
        from .context_schema import check_context
        current = self.get_context(context_id, owner)
        check_context({**current, 'confirmed': True}, version=version)
        with self.cursor() as cur:
            cur.execute("UPDATE contexts SET confirmed=TRUE WHERE id=%s AND owner=%s AND version=%s",
                        (context_id, owner, version))
            if cur.rowcount != 1:
                raise ValueError('Stale context version')
        return self.get_context(context_id, owner)

    def invalidate_context(self, context_id: str, owner: str, version: int) -> Dict[str, Any]:
        with self.cursor() as cur:
            cur.execute("UPDATE contexts SET confirmed=FALSE, version=version+1 WHERE id=%s AND owner=%s AND version=%s",
                        (context_id, owner, version))
            if cur.rowcount != 1:
                raise ValueError('Stale context version')
        return self.get_context(context_id, owner)
