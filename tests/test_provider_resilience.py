import asyncio
import json
import httpx
import pytest

from heschema.providers import Provider, ProviderError

MESSAGES = [{"role": "system", "content": "Return JSON"}, {"role": "user", "content": "Test"}]


def test_provider_retries_transient_transport_error(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-resilience-key")
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) < 3:
            raise httpx.ConnectError("SSL handshake reset or connection dropped", request=request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "{\"status\": \"ok\"}"}}]})

    async def check():
        # Monkeypatch asyncio.sleep to fast-forward backoff in tests
        orig_sleep = asyncio.sleep
        sleep_durations = []

        async def fast_sleep(sec):
            sleep_durations.append(sec)

        monkeypatch.setattr(asyncio, "sleep", fast_sleep)
        provider = Provider("groq", interval=0, transport=httpx.MockTransport(handler))
        try:
            result = await provider.generate(MESSAGES)
            assert result.text == "{\"status\": \"ok\"}"
            assert len(calls) == 3
            assert len(sleep_durations) == 2  # slept twice
        finally:
            await provider.close()

    asyncio.run(check())


def test_provider_retries_transient_timeout(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-resilience-key")
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) < 2:
            raise httpx.ReadTimeout("Read timed out", request=request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "{\"status\": \"recovered\"}"}}]})

    async def check():
        sleep_durations = []

        async def fast_sleep(sec):
            sleep_durations.append(sec)

        monkeypatch.setattr(asyncio, "sleep", fast_sleep)
        provider = Provider("groq", interval=0, transport=httpx.MockTransport(handler))
        try:
            result = await provider.generate(MESSAGES)
            assert result.text == "{\"status\": \"recovered\"}"
            assert len(calls) == 2
            assert len(sleep_durations) == 1
        finally:
            await provider.close()

    asyncio.run(check())


def test_provider_exhausts_retries_on_persistent_network_error(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-resilience-key")
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ConnectError("Network unreachable", request=request)

    async def check():
        async def fast_sleep(sec):
            pass

        monkeypatch.setattr(asyncio, "sleep", fast_sleep)
        provider = Provider("groq", interval=0, transport=httpx.MockTransport(handler))
        try:
            with pytest.raises(ProviderError) as exc_info:
                await provider.generate(MESSAGES)
            assert exc_info.value.code == "network_error"
            assert len(calls) == 4  # 1 initial + 3 retries
        finally:
            await provider.close()

    asyncio.run(check())
