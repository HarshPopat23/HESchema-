"""TDD test suite for pluggable PostgreSQL StateStore and multi-pod horizontal scaling."""

import json
from unittest.mock import MagicMock, patch

import pytest

from heschema.contracts import Contract
from heschema.state import BaseStateStore, PostgresStateStore, SQLiteStateStore, StateStore


def test_state_store_factory_routing(tmp_path):
    """Verify StateStore routes properly based on URI scheme."""
    sqlite_store = StateStore(tmp_path / "test.sqlite")
    assert isinstance(sqlite_store, SQLiteStateStore)
    assert hasattr(sqlite_store, "path")

    # With sqlite:// URI
    sqlite_uri_store = StateStore(f"sqlite:///{tmp_path}/test2.sqlite")
    assert isinstance(sqlite_uri_store, SQLiteStateStore)

    # With postgresql:// and postgres:// URIs
    pg_store = StateStore("postgresql://postgres:secret@db.internal:5432/heschema")
    assert isinstance(pg_store, PostgresStateStore)
    assert pg_store.uri == "postgresql://postgres:secret@db.internal:5432/heschema"

    pg_store2 = StateStore("postgres://user:pass@remote:5432/app")
    assert isinstance(pg_store2, PostgresStateStore)


def test_postgres_state_store_lifecycle_and_optimistic_locking():
    """Verify PostgreSQL SQL operations, row transformations, and optimistic concurrency."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # In-memory storage for simulated Postgres rows
    db_states = {}

    def fake_execute(query, params=None):
        query_str = query.strip()
        if "CREATE TABLE IF NOT EXISTS states" in query_str or "CREATE TABLE IF NOT EXISTS contexts" in query_str:
            mock_cursor.rowcount = 0
            return mock_cursor

        if query_str.startswith("INSERT INTO states"):
            sid, owner, ver, prompt, payload, conf = params
            db_states[sid] = {
                "id": sid,
                "owner": owner,
                "version": ver,
                "prompt": prompt,
                "payload": payload,
                "confirmed": conf,
            }
            mock_cursor.rowcount = 1
            return mock_cursor

        if query_str.startswith("SELECT * FROM states WHERE id=%s AND owner=%s"):
            sid, owner = params
            row = db_states.get(sid)
            if row and row["owner"] == owner:
                mock_cursor.fetchone.return_value = dict(row)
            else:
                mock_cursor.fetchone.return_value = None
            return mock_cursor

        if query_str.startswith("UPDATE states SET confirmed=TRUE WHERE id=%s AND owner=%s AND version=%s"):
            sid, owner, ver = params
            row = db_states.get(sid)
            if row and row["owner"] == owner and row["version"] == ver:
                row["confirmed"] = True
                mock_cursor.rowcount = 1
            else:
                mock_cursor.rowcount = 0
            return mock_cursor

        if query_str.startswith("UPDATE states SET payload=%s, version=version+1, confirmed=FALSE WHERE id=%s AND owner=%s AND version=%s"):
            payload, sid, owner, ver = params
            row = db_states.get(sid)
            if row and row["owner"] == owner and row["version"] == ver:
                row["payload"] = payload
                row["version"] += 1
                row["confirmed"] = False
                mock_cursor.rowcount = 1
            else:
                mock_cursor.rowcount = 0
            return mock_cursor

        return mock_cursor

    mock_cursor.execute.side_effect = fake_execute

    with patch("psycopg.connect", return_value=mock_conn):
        store = PostgresStateStore("postgresql://test:test@localhost:5432/test")

        # 1. Create state
        res = store.create("tenant-alpha", "Draft travel plan", {"destination": "Berlin", "days": 3})
        state_id = res["id"]
        assert res["owner"] == "tenant-alpha"
        assert res["version"] == 1
        assert res["confirmed"] is False
        assert res["state"] == {"destination": "Berlin", "days": 3}

        # 2. Get state
        got = store.get(state_id, "tenant-alpha")
        assert got["id"] == state_id
        assert got["state"] == {"destination": "Berlin", "days": 3}

        # 3. Optimistic locking on confirm: Stale version fails
        with pytest.raises(ValueError, match="State ownership/version mismatch"):
            store.confirm(state_id, "tenant-alpha", version=999)

        # 4. Valid confirm succeeds
        confirmed = store.confirm(state_id, "tenant-alpha", version=1)
        assert confirmed["confirmed"] is True
        assert confirmed["version"] == 1

        # 5. Replace state increments version and resets confirmed
        replaced = store.replace(state_id, "tenant-alpha", version=1, state={"destination": "Munich", "days": 5})
        assert replaced["version"] == 2
        assert replaced["confirmed"] is False
        assert replaced["state"] == {"destination": "Munich", "days": 5}


def test_api_discovers_database_url_from_environment(tmp_path, monkeypatch):
    """Verify FastAPI create_app discovers HESCHEMA_DATABASE_URL."""
    from heschema.api import create_app

    monkeypatch.setenv("HESCHEMA_DATABASE_URL", "postgresql://user:pass@k8s-pg-service:5432/heschema_prod")
    monkeypatch.delenv("HESCHEMA_API_TOKEN", raising=False)

    with patch("psycopg.connect") as mock_pg_connect:
        mock_conn = MagicMock()
        mock_pg_connect.return_value = mock_conn
        app = create_app()
        assert app is not None
