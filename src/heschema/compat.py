"""OpenAI-compatible chat completions endpoint for Sourcemeta CLI and interoperability trials."""

import secrets
import time
from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .jsonio import canonical
from .providers import Provider, ProviderError
from .schema import check_schema


class OpenAISchemaObject(BaseModel):
    name: str = "schema"
    schema_: dict[str, Any] = Field(alias="schema")
    strict: bool = True


class ResponseFormat(BaseModel):
    type: str
    json_schema: OpenAISchemaObject | None = None


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    response_format: ResponseFormat | None = None
    stream: bool | None = False
    max_tokens: int | None = None
    max_completion_tokens: int | None = None
    temperature: float | None = None
    seed: int | None = None
    heschema_mode: str = "native_schema"  # "native_schema" | "prompt_only"
    # Unsupported options to detect explicitly
    tools: list[Any] | None = None
    tool_choice: Any | None = None
    n: int | None = None


def make_error_response(status_code: int, message: str, error_type: str = "invalid_request_error", param: str | None = None, code: str | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "message": message,
                "type": error_type,
                "param": param,
                "code": code,
            }
        },
    )


async def handle_chat_completion(raw_body: dict[str, Any], operator_identity: str) -> JSONResponse:
    # 1. Parsing & validation
    # Check for stream: true
    if raw_body.get("stream") is True:
        return make_error_response(400, "Streaming is not supported by this endpoint; set stream to false or omit it.", param="stream", code="streaming_not_supported")

    if raw_body.get("tools") or raw_body.get("tool_choice"):
        return make_error_response(400, "Tools and tool calls are not supported by this endpoint.", param="tools", code="tools_not_supported")

    if raw_body.get("n") is not None and raw_body.get("n") > 1:
        return make_error_response(400, "Multiple completions (n > 1) are not supported.", param="n", code="n_not_supported")

    try:
        req = ChatCompletionRequest.model_validate(raw_body)
    except Exception as exc:
        return make_error_response(400, f"Malformed chat completion request: {exc}", code="bad_request")

    if not req.model.strip():
        return make_error_response(400, "Field 'model' must be a non-empty string.", param="model", code="missing_model")

    if not req.messages:
        return make_error_response(400, "Field 'messages' must contain at least one message.", param="messages", code="empty_messages")

    for idx, msg in enumerate(req.messages):
        if msg.role not in {"system", "user", "assistant"}:
            return make_error_response(400, f"Unsupported message role '{msg.role}' at index {idx}.", param=f"messages[{idx}].role", code="unsupported_role")
        if not isinstance(msg.content, str):
            return make_error_response(400, f"Message content at index {idx} must be a string.", param=f"messages[{idx}].content", code="invalid_content")

    # Token limits checking
    if req.max_tokens is not None and req.max_completion_tokens is not None:
        if req.max_tokens != req.max_completion_tokens:
            return make_error_response(400, f"Conflicting token limits: max_tokens={req.max_tokens} vs max_completion_tokens={req.max_completion_tokens}", param="max_tokens", code="conflicting_parameters")
        max_tokens = req.max_tokens
    elif req.max_tokens is not None:
        max_tokens = req.max_tokens
    elif req.max_completion_tokens is not None:
        max_tokens = req.max_completion_tokens
    else:
        max_tokens = 1024

    if max_tokens <= 0:
        return make_error_response(400, "Token limit must be greater than 0", param="max_tokens", code="invalid_token_limit")

    # Mode checking
    mode = req.heschema_mode or "native_schema"
    if mode not in {"native_schema", "prompt_only"}:
        return make_error_response(400, f"Invalid heschema_mode '{mode}'. Supported modes: 'native_schema', 'prompt_only'.", param="heschema_mode", code="invalid_mode")

    # Response format checking
    if not req.response_format or req.response_format.type != "json_schema" or not req.response_format.json_schema:
        return make_error_response(400, "Endpoint requires response_format of type 'json_schema' with nested 'json_schema' object.", param="response_format", code="unsupported_response_format")

    json_schema_obj = req.response_format.json_schema
    schema_dict = json_schema_obj.schema_
    strict = json_schema_obj.strict

    if mode == "prompt_only" and strict:
        return make_error_response(400, "Prompt-only mode does not provide native schema enforcement; strict must be set to false.", param="response_format.json_schema.strict", code="strict_mode_unsupported")

    # Draft 2020-12 schema validation
    try:
        check_schema(schema_dict)
    except ValueError as exc:
        return make_error_response(422, f"Invalid JSON Schema: {exc}", param="response_format.json_schema.schema", code="invalid_schema")

    # Provider resolution
    # Local Ollama or mock
    provider_name = "mock" if (req.model.startswith("mock") or req.model == "offline-stub") else "ollama"

    # Upstream message preparation
    messages_payload = [{"role": m.role, "content": m.content} for m in req.messages]
    format_arg = None

    if mode == "native_schema":
        format_arg = schema_dict
    else:
        # Prompt-only mode: schema grounding message appended
        grounding_content = (
            f"\n\n[SCHEMA CONSTRAINT]\nYou must output ONLY valid JSON adhering strictly to this JSON Schema:\n{canonical(schema_dict)}"
        )
        messages_payload.append({"role": "user", "content": grounding_content})
        format_arg = None

    try:
        provider = Provider(provider_name, model=req.model)
    except Exception as exc:
        return make_error_response(400, f"Failed to initialize provider: {exc}", code="provider_init_failed")

    try:
        result = await provider.generate(
            messages=messages_payload,
            seed=req.seed if req.seed is not None else 0,
            max_tokens=max_tokens,
            temperature=req.temperature,
            format_schema=format_arg,
            retry=False,  # Single-generation policy without auto-retries for trials
        )
    except ProviderError as exc:
        err_msg = str(exc)
        if "rate limit" in err_msg.lower() or "timeout" in err_msg.lower() or "timed out" in err_msg.lower():
            return make_error_response(504, f"Upstream provider timed out or rate limited: {err_msg}", error_type="timeout_error", code="gateway_timeout")
        return make_error_response(502, f"Upstream generation failed: {err_msg}", error_type="api_error", code="bad_gateway")
    except Exception as exc:
        return make_error_response(500, f"Internal completion error: {exc}", error_type="api_error", code="internal_error")
    finally:
        await provider.close()

    # Determine finish reason
    raw_finish = result.metadata.get("finish_reason")
    if raw_finish in {"stop", "length"}:
        finish_reason = raw_finish
    elif raw_finish:
        finish_reason = str(raw_finish)
    else:
        finish_reason = "stop"

    usage_data = None
    if result.input_tokens is not None and result.output_tokens is not None:
        usage_data = {
            "prompt_tokens": result.input_tokens,
            "completion_tokens": result.output_tokens,
            "total_tokens": result.input_tokens + result.output_tokens,
        }

    envelope = {
        "id": f"chatcmpl-{secrets.token_hex(12)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": result.model or req.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result.text,  # MUST remain raw string, no unescaping, parsing or strip
                },
                "finish_reason": finish_reason,
            }
        ],
    }
    if usage_data:
        envelope["usage"] = usage_data

    return JSONResponse(status_code=200, content=envelope)
