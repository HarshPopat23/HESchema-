import asyncio
import json

import httpx
import pytest

from heschema.capabilities import capability_profile
from heschema.providers import Provider, ProviderError


def test_groq_strict_payload_keeps_schema_and_messages(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-only-key")
    messages = [{"role": "user", "content": "Return a whole JSON value"}]
    schema = {"oneOf": [{"type": "integer"}, {"type": "number", "minimum": 0}]}

    async def check():
        p = Provider("groq", interval=0)
        try:
            _, headers, prompt = p.request(messages, 42, 1024, 0)
            _, _, native = p.request(messages, 42, 1024, 0, format_schema=schema)
            assert headers["User-Agent"] == "HESchema/0.1"
            assert prompt["messages"] == native["messages"] == messages
            assert "response_format" not in prompt
            assert native["response_format"] == {
                "type": "json_schema",
                "json_schema": {"name": "heschema_output", "strict": True, "schema": schema},
            }
            assert prompt["reasoning_effort"] == native["reasoning_effort"] == "low"
            assert "seed" not in native
            assert capability_profile("groq", "native_original")["adapterStatus"] == "implemented"
        finally:
            await p.close()

    asyncio.run(check())


def test_groq_metadata_and_native_rejection_have_no_fallback(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-only-key")
    seen = []

    def handler(req):
        seen.append(json.loads(req.content))
        if len(seen) == 1:
            return httpx.Response(400, json={"error": {"message": "unsupported schema"}})
        return httpx.Response(
            200,
            json={
                "model": "openai/gpt-oss-20b",
                "id": "test-response",
                "choices": [
                    {"message": {"content": "{}", "reasoning": "internal"}, "finish_reason": "stop"}
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 4},
            },
            headers={"x-ratelimit-remaining-requests": "999"},
        )

    async def check():
        p = Provider("groq", interval=0, transport=httpx.MockTransport(handler))
        try:
            with pytest.raises(ProviderError) as exc:
                await p.generate([], format_schema={"type": "object"}, retry=False)
            assert exc.value.code == "request_rejected" and len(seen) == 1
            g = await p.generate([], format_schema={"type": "object"}, retry=False)
            assert g.metadata["nativeStrictRequested"] is True
            assert g.metadata["rateLimitHeaders"]["x-ratelimit-remaining-requests"] == "999"
            assert g.reasoning == "internal" and g.input_tokens == 10 and g.output_tokens == 4
        finally:
            await p.close()

    asyncio.run(check())
