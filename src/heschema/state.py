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
        with self.connect() as db:
            cursor = db.execute("UPDATE states SET confirmed=1 WHERE id=? AND owner=? AND version=?",
                                (state_id, owner, version))
            if cursor.rowcount != 1:
                raise ValueError("State ownership/version mismatch")
        return self.get(state_id, owner)

    def replace(self, state_id, owner, version, state):
        with self.connect() as db:
            cursor = db.execute("UPDATE states SET payload=?,version=version+1,confirmed=0 WHERE id=? AND owner=? AND version=?",
                                (canonical(state), state_id, owner, version))
            if cursor.rowcount != 1:
                raise ValueError("Stale state or unknown owner")
        return self.get(state_id, owner)
