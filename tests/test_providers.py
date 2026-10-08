import asyncio
import json

import httpx
import pytest

from heschema.providers import Provider, ProviderError, registry, tavily_search

MESSAGES = [{"role": "system", "content": "Return JSON"}, {"role": "user", "content": "Test"}]


@pytest.mark.parametrize("name", ["groq", "mistral", "gemini", "openrouter", "huggingface", "openai", "anthropic", "ollama"])
def test_provider_protocol_and_usage(name, monkeypatch):
    config = registry()[name]
    if config.get("key_env"):
        monkeypatch.setenv(config["key_env"], "test-only-key")
    def handler(request):
        payload = json.loads(request.content)
        assert payload["model"] == config["model"]
        assert "response_format" not in payload and "tools" not in payload
        if name == "openai":
            assert request.url.path.endswith("/responses") and payload["store"] is False
            body = {"output": [{"content": [{"type": "output_text", "text": "{}"}]}], "usage": {"input_tokens": 10, "output_tokens": 2}}
        elif name == "anthropic":
            assert payload["system"] == MESSAGES[0]["content"]
            assert request.headers["x-api-key"] == "test-only-key"
            body = {"content": [{"type": "text", "text": "{}"}], "usage": {"input_tokens": 7, "cache_read_input_tokens": 3, "output_tokens": 2}}
        elif name == "ollama":
            assert payload["stream"] is False and payload["options"]["seed"] == 42
            body = {"message": {"content": "{}"}, "prompt_eval_count": 10, "eval_count": 2}
        else:
            assert request.url.path.endswith("/chat/completions")
            body = {"choices": [{"message": {"content": "{}"}}], "usage": {"prompt_tokens": 10, "completion_tokens": 2}}
        return httpx.Response(200, json=body)
    async def check():
        provider = Provider(name, interval=0, transport=httpx.MockTransport(handler))
        try:
            result = await provider.generate(MESSAGES, seed=42)
            assert result.text == "{}" and result.input_tokens == 10 and result.output_tokens == 2
        finally:
            await provider.close()
    asyncio.run(check())


def test_errors_do_not_expose_response_or_key(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "private-test-key")
    async def check():
        provider = Provider("groq", interval=0, transport=httpx.MockTransport(lambda r: httpx.Response(401, text="private-test-key")))
        try:
            with pytest.raises(ProviderError) as exc:
                await provider.generate(MESSAGES)
            assert "private-test-key" not in str(exc.value)
            assert "401" in str(exc.value)
        finally:
            await provider.close()
    asyncio.run(check())


def test_transport_retry_separate_from_llm_repair(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-only-key")
    calls = []
    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"retry-after": "0"})
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})
    async def check():
        provider = Provider("groq", interval=0, transport=httpx.MockTransport(handler))
        try:
            result = await provider.generate(MESSAGES)
            assert result.transport_retries == 1 and result.input_tokens is None
        finally:
            await provider.close()
    asyncio.run(check())


def test_tavily_is_search_not_llm(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-only-key")
    assert "tavily" not in registry()
    def handler(request):
        assert request.url.host == "api.tavily.com"
        assert json.loads(request.content)["query"] == "MCP"
        return httpx.Response(200, json={"results": []})
    result = asyncio.run(tavily_search("MCP", transport=httpx.MockTransport(handler)))
    assert result == {"results": []}
