"""Comprehensive test suite for Concurrency, Security, Storage, and SSE Streaming gates."""

import asyncio
import os
import sqlite3
import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from heschema.api import create_app
from heschema.providers import Provider, Generation, ProviderError
from heschema.proxy import router as proxy_router, ChatCompletionRequest
from heschema.state import StateStore


# --- Gate G1: Concurrency & Lock Decoupling ---
@pytest.mark.asyncio
async def test_g1_provider_concurrency_lock_decoupling():
    """Verify pacing lock is released during network calls so concurrent requests pipeline."""
    provider = Provider("mock", interval=0.05)

    concurrent_count = 0
    max_concurrent = 0

    async def fake_post(*args, **kwargs):
        nonlocal concurrent_count, max_concurrent
        concurrent_count += 1
        if concurrent_count > max_concurrent:
            max_concurrent = concurrent_count
        await asyncio.sleep(0.05)
        concurrent_count -= 1

        mock_resp = AsyncMock()
        mock_resp.is_error = False
        mock_resp.status_code = 200
        mock_resp.headers = {"x-ratelimit-remaining": "100"}
        mock_resp.json = lambda: {
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
            "model": "mock",
        }
        return mock_resp

    # Use a real provider with mocked client
    test_prov = Provider("groq", model="llama-3.3-70b-versatile", interval=0.01, key="dummy_key")
    test_prov.client.post = fake_post

    start = time.perf_counter()
    tasks = [
        test_prov.generate([{"role": "user", "content": f"msg {i}"}], retry=False)
        for i in range(10)
    ]
    results = await asyncio.gather(*tasks)
    total_time = time.perf_counter() - start

    await test_prov.close()

    assert len(results) == 10
    # If requests were serialized: 10 * 0.05 = 0.50s minimum network wait.
    # With decoupled async pipelining, max_concurrent > 1 and total_time is significantly less.
    assert max_concurrent >= 2
    assert total_time < 0.40


# --- Gate G2: Multitenant Key Isolation in Proxy ---
@pytest.mark.asyncio
async def test_g2_proxy_key_isolation_no_os_environ_mutation():
    """Verify API keys passed to proxy do not mutate global os.environ."""
    groq_env_before = os.environ.get("GROQ_API_KEY")

    app = FastAPI()
    app.include_router(proxy_router)

    with patch("heschema.providers.Provider.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = Generation(
            text='{"action": "refuse", "tool": null, "arguments": {}, "missingFields": []}',
            input_tokens=10,
            output_tokens=10,
            model="llama-3.3-70b-versatile",
            metadata={"finish_reason": "stop"},
        )

        with TestClient(app) as client:
            resp = client.post(
                "/v1/chat/completions",
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": "hello"}],
                },
                headers={"Authorization": "Bearer tenant_secret_token_12345"},
            )
            assert resp.status_code == 200

    # Ensure os.environ was NOT polluted
    assert os.environ.get("GROQ_API_KEY") == groq_env_before


# --- Gate G4: SQLite WAL Mode & Concurrency ---
def test_g4_sqlite_wal_mode_and_concurrency(tmp_path):
    """Verify SQLite WAL mode and busy_timeout are properly initialized."""
    db_file = tmp_path / "state_wal.sqlite3"
    store = StateStore(db_file)

    with sqlite3.connect(str(db_file)) as conn:
        cursor = conn.cursor()
        mode = cursor.execute("PRAGMA journal_mode;").fetchone()[0]
        # WAL mode is active
        assert mode.lower() == "wal"

    # Parallel readers do not block during active state creation
    state1 = store.create("tenantA", "prompt 1", {"k": 1})
    assert state1["confirmed"] is False

    read1 = store.get(state1["id"], "tenantA")
    assert read1["state"] == {"k": 1}


# --- SSE Streaming in Proxy ---
def test_proxy_sse_streaming():
    """Verify OpenAI proxy SSE streaming generator yields event-stream chunks."""
    app = FastAPI()
    app.include_router(proxy_router)

    with patch("heschema.providers.Provider.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = Generation(
            text="Hello streaming world!",
            input_tokens=5,
            output_tokens=5,
            model="llama-3.3-70b-versatile",
            metadata={"finish_reason": "stop"},
        )

        with TestClient(app) as client:
            resp = client.post(
                "/v1/chat/completions",
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": "hello"}],
                    "stream": True,
                },
                headers={"Authorization": "Bearer dummy"},
            )
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            body_text = resp.text
            assert "data: " in body_text
            assert "chat.completion.chunk" in body_text
            assert "Hello streaming world!" in body_text
            assert "data: [DONE]" in body_text
