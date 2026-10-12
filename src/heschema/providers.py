"""Providers return text only. Schema prompting and constrained decoding stay separate."""

import asyncio
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from dotenv import load_dotenv

from .jsonio import canonical, read_json

ROOT = Path(__file__).resolve().parents[2]


class ProviderError(RuntimeError):
    """Sanitized provider failure: never include keys or HTTP response bodies."""

    def __init__(self, message, *, code="provider_error", status=None, requests=1, elapsed_ms=None):
        super().__init__(message)
        self.code, self.status, self.requests, self.elapsed_ms = code, status, requests, elapsed_ms

    def diagnostic(self):
        return {"code": self.code, "httpStatus": self.status, "message": str(self)[:500],
                "requests": self.requests, "elapsedMs": self.elapsed_ms}


@dataclass
class Generation:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    model: str | None = None
    transport_retries: int = 0
    latency_ms: float = 0
    metadata: dict = field(default_factory=dict)
    reasoning: str | None = None

    @property
    def completion(self):
        reason = self.metadata.get("finish_reason")
        if reason in {"length", "max_tokens", "max_output_tokens"}:
            return "truncated"
        if not self.text:
            return "empty"
        if reason in {"stop", "end_turn", "stop_sequence", "completed"}:
            return "completed"
        return "unknown"

    def diagnostic(self):
        return {"outputPresent": bool(self.text), "completion": self.completion,
                "finishReason": self.metadata.get("finish_reason"), "model": self.model,
                "modelConfirmed": self.metadata.get("resolvedModelConfirmed", False),
                "usage": {"inputTokens": self.input_tokens, "outputTokens": self.output_tokens},
                "transportRetries": self.transport_retries, "latencyMs": self.latency_ms,
                "durationsMs": self.metadata.get("durationsMs", {}),
                "reasoningPresent": bool(self.reasoning)}


def registry():
    return read_json(ROOT / "config/providers.json")


class Provider:
    def __init__(self, name, model=None, interval=None, transport=None):
        load_dotenv(ROOT / ".env", override=False)
        configs = registry()
        if name not in configs:
            raise ValueError(f"Unknown provider: {name}")
        self.name, self.config = name, configs[name].copy()
        self.model = model or self.config["model"]
        self.interval = float(os.getenv("HESCHEMA_REQUEST_INTERVAL", "3")) if interval is None else interval
        self.last_request = 0
        self.lock = asyncio.Lock()
        self.key = os.getenv(self.config.get("key_env", ""), "")
        if self.config["kind"] not in {"mock", "ollama"} and not self.key:
            raise ProviderError(f"Set {self.config['key_env']} in the backend .env")
        if self.interval < 0:
            raise ValueError("Request interval must be nonnegative")
        default_timeout = 180.0 if self.config["kind"] == "ollama" else 120.0
        env_timeout = os.getenv("OLLAMA_TIMEOUT") if self.config["kind"] == "ollama" else os.getenv("HESCHEMA_REQUEST_TIMEOUT")
        self.timeout = float(env_timeout) if env_timeout else default_timeout
        self.client = None if self.config["kind"] == "mock" else httpx.AsyncClient(timeout=self.timeout, transport=transport)

    async def close(self):
        if self.client is not None:
            await self.client.aclose()

    def request(self, messages, seed, max_tokens, temperature, format_schema=None):
        config, kind = self.config, self.config["kind"]
        if format_schema is not None and kind not in {"ollama", "mock"}:
            raise ProviderError("Native schema mode is not implemented for this adapter", code="unsupported_mode", requests=0)
        base = (os.getenv("OLLAMA_BASE_URL", config.get("base_url")) if kind == "ollama" else config.get("base_url", "")).rstrip("/")
        headers = {"Content-Type": "application/json"}
        if kind == "responses":
            payload = {"model": self.model, "input": messages, "max_output_tokens": max_tokens, "store": False}
            if temperature is not None:
                payload["temperature"] = temperature
            return base + "/responses", {**headers, "Authorization": "Bearer " + self.key}, payload
        if kind == "anthropic":
            payload = {"model": self.model, "max_tokens": max_tokens,
                       "system": messages[0]["content"], "messages": messages[1:]}
            if temperature is not None:
                payload["temperature"] = temperature
            return base + "/messages", {**headers, "x-api-key": self.key, "anthropic-version": "2023-06-01"}, payload
        if kind == "ollama":
            options = {"seed": seed, "num_predict": max_tokens}
            if temperature is not None:
                options["temperature"] = temperature
            payload = {"model": self.model, "messages": messages, "stream": False, "options": options}
            if format_schema is not None:
                payload["format"] = format_schema
            if os.getenv("OLLAMA_THINK", "false").lower() in {"false", "0", "no"}:
                payload["think"] = False
            return base + "/api/chat", headers, payload
        payload = {"model": self.model, "messages": messages, "max_tokens": max_tokens}
        if temperature is not None:
            payload["temperature"] = temperature
        if config.get("seed_supported"):
            payload["seed"] = seed
        return base + "/chat/completions", {**headers, "Authorization": "Bearer " + self.key}, payload

    async def generate(self, messages, seed=0, max_tokens=1024, temperature=None, format_schema=None, retry=True):
        if self.config["kind"] == "mock":
            # Fixed response independent of schema and hidden gold. A pipeline smoke
            # test can never serve as empirical evidence of model improvement.
            return Generation(canonical({"action": "refuse", "tool": None, "arguments": {},
                                         "missingFields": [], "reason": "Offline stub"}),
                              0, 0, "offline-stub", metadata={"synthetic": True, "finish_reason": "stop"})
        async with self.lock:
            delay = self.interval - (time.monotonic() - self.last_request)
            if delay > 0:
                await asyncio.sleep(delay)
            start = time.perf_counter()
            url, headers, payload = self.request(messages, seed, max_tokens, temperature, format_schema=format_schema)
            attempts = 0
            while True:
                self.last_request = time.monotonic()
                try:
                    response = await self.client.post(url, headers=headers, json=payload)
                except httpx.TimeoutException:
                    raise ProviderError(f"{self.name}: request timed out after {int(self.timeout)}s", code="timeout", requests=attempts + 1, elapsed_ms=(time.perf_counter() - start) * 1000) from None
                except httpx.RequestError:
                    if not retry or attempts >= 2:
                        raise ProviderError(f"{self.name}: network request failed", code="network_error", requests=attempts + 1) from None
                    attempts += 1
                    await asyncio.sleep(min(2 ** attempts, 8))
                    continue
                if response.status_code in {429, 500, 502, 503, 504} and retry and attempts < 2:
                    attempts += 1
                    try:
                        retry_after = float(response.headers.get("retry-after", 2 ** attempts))
                    except ValueError:
                        retry_after = 2 ** attempts
                    if retry_after > 30:
                        raise ProviderError(f"{self.name}: rate limited; resume later")
                    await asyncio.sleep(max(self.interval, retry_after))
                    continue
                if response.is_error:
                    code = "request_rejected" if response.status_code in {400, 422} else "authentication_error" if response.status_code in {401, 403} else "provider_error"
                    raise ProviderError(f"{self.name}: HTTP {response.status_code}; check credentials, model and account limits", code=code, status=response.status_code, requests=attempts + 1, elapsed_ms=(time.perf_counter() - start) * 1000)
                try:
                    data = response.json()
                    kind = self.config["kind"]
                    finish_reason = None
                    reasoning = None
                    if kind == "responses":
                        text = "".join(c["text"] for item in data.get("output", []) for c in item.get("content", []) if c.get("type") == "output_text")
                        usage = data.get("usage", {})
                        inp, out = usage.get("input_tokens"), usage.get("output_tokens")
                        finish_reason = "completed" if data.get("status") == "completed" else data.get("incomplete_details", {}).get("reason")
                    elif kind == "anthropic":
                        text = "".join(c["text"] for c in data["content"] if c["type"] == "text")
                        usage = data.get("usage", {})
                        # Include cache token reads/writes in usage; precise cache pricing
                        # needs user-supplied effective rates and is explicitly approximate.
                        inp = sum(usage.get(k, 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")) if "input_tokens" in usage else None
                        out = usage.get("output_tokens")
                        finish_reason = data.get("stop_reason")
                    elif kind == "ollama":
                        text = data["message"]["content"]
                        reasoning = data["message"].get("thinking")
                        inp, out = data.get("prompt_eval_count"), data.get("eval_count")
                        finish_reason = data.get("done_reason")
                    else:
                        text = data["choices"][0]["message"]["content"]
                        usage = data.get("usage", {})
                        inp, out = usage.get("prompt_tokens"), usage.get("completion_tokens")
                        finish_reason = data["choices"][0].get("finish_reason")
                    if not isinstance(text, str):
                        raise ValueError("Missing text")
                except (ValueError, TypeError, KeyError, IndexError, AttributeError):
                    raise ProviderError(f"{self.name}: unexpected response structure") from None
                meta = {"resolvedModelConfirmed": bool(data.get("model"))}
                if kind == "ollama":
                    meta["durationsMs"] = {key: data[source] / 1e6 for key, source in
                                           (("total", "total_duration"), ("load", "load_duration"),
                                            ("promptEvaluation", "prompt_eval_duration"), ("generation", "eval_duration"))
                                           if isinstance(data.get(source), (int, float))}
                if finish_reason is not None:
                    meta["finish_reason"] = finish_reason
                return Generation(text, inp, out, data.get("model", self.model), attempts,
                                  (time.perf_counter() - start) * 1000,
                                  meta, reasoning)


async def tavily_search(query, max_results=5, transport=None):
    """Search integration, excluded from LLM ranking. No calls during benchmark generation."""
    load_dotenv(ROOT / ".env", override=False)
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        raise ProviderError("Set TAVILY_API_KEY in backend .env")
    try:
        async with httpx.AsyncClient(timeout=30, transport=transport) as client:
            response = await client.post("https://api.tavily.com/search",
                                         headers={"Authorization": "Bearer " + key},
                                         json={"query": query, "max_results": max_results, "search_depth": "basic"})
            if response.is_error:
                raise ProviderError(f"Tavily: HTTP {response.status_code}")
            return response.json()
    except (httpx.RequestError, ValueError):
        raise ProviderError("Tavily: network request failed or invalid response") from None
