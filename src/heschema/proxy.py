"""OpenAI / LiteLLM reverse-proxy routes for transparent HESchema validation and repair."""

import json
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .contracts import Contract
from .guard import guard
from .jsonio import loads
from .providers import Provider, ProviderError, registry

router = APIRouter(prefix="/v1", tags=["OpenAI Proxy"])


class ChatMessage(BaseModel):
    role: str
    content: Optional[str] = None
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Dict[str, Any]]
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Any] = None
    temperature: Optional[float] = 0.0
    max_tokens: Optional[int] = None
    seed: Optional[int] = 42
    stream: Optional[bool] = False


def _detect_provider(model: str) -> str:
    """Map model name to registered provider."""
    model_lower = model.lower()
    if "gpt" in model_lower or "o1" in model_lower or "o3" in model_lower:
        return "openai"
    if "claude" in model_lower:
        return "anthropic"
    if "gemini" in model_lower:
        return "gemini"
    if "mistral" in model_lower or "codestral" in model_lower:
        return "mistral"
    # Default to Groq or first available
    return "groq"


@router.get("/models")
async def list_models():
    """List available models compatible with the OpenAI SDK format."""
    reg = registry()
    data = []
    for prov_name, conf in reg.items():
        data.append({
            "id": conf["model"],
            "object": "model",
            "created": 1700000000,
            "owned_by": prov_name,
        })
    return {"object": "list", "data": data}


@router.post("/chat/completions")
async def chat_completions(
    request: Request,
    body: ChatCompletionRequest,
    authorization: Optional[str] = Header(None),
):
    """Transparently intercept tool calls, validate against contracts, and repair calculated fields."""

    # Extract API key if supplied in Authorization header
    api_key = None
    if authorization and authorization.startswith("Bearer "):
        api_key = authorization.split("Bearer ", 1)[1].strip()

    provider_name = _detect_provider(body.model)

    # Build tools lookup by name
    tools_by_name = {}
    if body.tools:
        for t in body.tools:
            if t.get("type") == "function" and "function" in t:
                fn = t["function"]
                tools_by_name[fn["name"]] = fn.get("parameters", {"type": "object"})

    provider = Provider(provider_name, model=body.model, interval=0, key=api_key)
    try:
        # Generate completion via provider
        gen = await provider.generate(
            body.messages,
            seed=body.seed or 42,
            max_tokens=body.max_tokens or 1024,
            temperature=body.temperature or 0.0,
        )
    except ProviderError as exc:
        raise HTTPException(status_code=exc.status or 502, detail=str(exc))
    finally:
        await provider.close()

    raw_text = gen.text
    tool_calls = []

    # Check if the output returned tool calls JSON or envelope
    try:
        parsed = loads(raw_text)
        if isinstance(parsed, dict):
            # If model returned tool envelope action
            if parsed.get("action") == "call_tool" and parsed.get("tool"):
                tool_name = parsed["tool"]
                arguments = parsed.get("arguments", {})
                params_schema = tools_by_name.get(tool_name, {"type": "object"})

                # Validate and repair with contract
                contract = Contract(
                    id=tool_name,
                    version="1.0",
                    outputKind="tool_envelope",
                    tool=tool_name,
                    schema=params_schema,
                )
                val = guard.validate(parsed, contract)
                # If calculations repaired arguments, use repaired values
                final_args = arguments
                calc_info = val.get("calculation", {})
                if calc_info.get("status") == "applied" and calc_info.get("values"):
                    for item in calc_info["values"]:
                        key = item["target"].lstrip("/").split("/")[0]
                        final_args[key] = item["value"]

                tool_calls.append({
                    "id": f"call_{int(time.time()*1000)}",
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(final_args),
                    },
                })
    except Exception:
        pass

    content = None if tool_calls else raw_text

    if body.stream:
        async def event_generator():
            cmpl_id = f"chatcmpl-{int(time.time()*1000)}"
            created_ts = int(time.time())

            # 1. Initial role announcement chunk
            chunk_init = {
                "id": cmpl_id,
                "object": "chat.completion.chunk",
                "created": created_ts,
                "model": body.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant"},
                        "finish_reason": None,
                    }
                ],
            }
            yield f"data: {json.dumps(chunk_init)}\n\n"

            # 2. Yield tool_calls or text content delta
            if tool_calls:
                for idx, tc in enumerate(tool_calls):
                    chunk_tc = {
                        "id": cmpl_id,
                        "object": "chat.completion.chunk",
                        "created": created_ts,
                        "model": body.model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {
                                    "tool_calls": [
                                        {
                                            "index": idx,
                                            "id": tc["id"],
                                            "type": "function",
                                            "function": {
                                                "name": tc["function"]["name"],
                                                "arguments": tc["function"]["arguments"],
                                            },
                                        }
                                    ]
                                },
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(chunk_tc)}\n\n"

                chunk_final = {
                    "id": cmpl_id,
                    "object": "chat.completion.chunk",
                    "created": created_ts,
                    "model": body.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": "tool_calls",
                        }
                    ],
                }
                yield f"data: {json.dumps(chunk_final)}\n\n"
            else:
                chunk_content = {
                    "id": cmpl_id,
                    "object": "chat.completion.chunk",
                    "created": created_ts,
                    "model": body.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": content or ""},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(chunk_content)}\n\n"

                chunk_final = {
                    "id": cmpl_id,
                    "object": "chat.completion.chunk",
                    "created": created_ts,
                    "model": body.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop",
                        }
                    ],
                }
                yield f"data: {json.dumps(chunk_final)}\n\n"

            yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    response_payload = {
        "id": f"chatcmpl-{int(time.time()*1000)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": body.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls if tool_calls else None,
                },
                "finish_reason": "tool_calls" if tool_calls else "stop",
            }
        ],
        "usage": {
            "prompt_tokens": gen.input_tokens or 0,
            "completion_tokens": gen.output_tokens or 0,
            "total_tokens": (gen.input_tokens or 0) + (gen.output_tokens or 0),
        },
    }
    return response_payload
