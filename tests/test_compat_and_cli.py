"""Tests for OpenAI-compatible chat completions endpoint and Sourcemeta CLI integration."""

import asyncio
import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient

from heschema.api import create_app
from heschema.cli_integration import (
    evaluate_document_diagnostics,
    generate_command_previews,
    probe_cli_support,
    resolve_cli_path,
)
from heschema.providers import Provider
from heschema.schema import SchemaEngine

SAMPLE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["username", "status"],
    "properties": {
        "username": {"type": "string", "minLength": 3},
        "status": {"type": "string", "enum": ["active", "inactive"]},
    },
    "additionalProperties": False,
}

VALID_REQ = {
    "model": "offline-stub",
    "messages": [{"role": "user", "content": "Create user alice99"}],
    "response_format": {
        "type": "json_schema",
        "json_schema": {
            "name": "schema",
            "strict": True,
            "schema": SAMPLE_SCHEMA,
        },
    },
}


def test_exact_sourcemeta_request_shape_accepted(tmp_path, monkeypatch):
    monkeypatch.delenv("HESCHEMA_API_TOKEN", raising=False)
    with TestClient(create_app(tmp_path / "state.sqlite")) as client:
        resp = client.post("/v1/chat/completions", json=VALID_REQ)
        assert resp.status_code == 200
        data = resp.json()
        assert data["object"] == "chat.completion"
        assert data["id"].startswith("chatcmpl-")
        assert len(data["choices"]) == 1
        choice = data["choices"][0]
        assert choice["index"] == 0
        assert choice["message"]["role"] == "assistant"
        assert isinstance(choice["message"]["content"], str)
        assert choice["finish_reason"] in {"stop", "length"}


def test_streaming_and_unsupported_options_rejected(tmp_path, monkeypatch):
    monkeypatch.delenv("HESCHEMA_API_TOKEN", raising=False)
    with TestClient(create_app(tmp_path / "state.sqlite")) as client:
        # stream: true
        r_stream = client.post("/v1/chat/completions", json={**VALID_REQ, "stream": True})
        assert r_stream.status_code == 400
        assert r_stream.json()["error"]["code"] == "streaming_not_supported"

        # tools
        r_tools = client.post("/v1/chat/completions", json={**VALID_REQ, "tools": [{"type": "function"}]})
        assert r_tools.status_code == 400
        assert r_tools.json()["error"]["code"] == "tools_not_supported"

        # n > 1
        r_n = client.post("/v1/chat/completions", json={**VALID_REQ, "n": 2})
        assert r_n.status_code == 400
        assert r_n.json()["error"]["code"] == "n_not_supported"

        # empty model
        r_m = client.post("/v1/chat/completions", json={**VALID_REQ, "model": "  "})
        assert r_m.status_code == 400

        # empty messages
        r_msg = client.post("/v1/chat/completions", json={**VALID_REQ, "messages": []})
        assert r_msg.status_code == 400

        # invalid role
        r_role = client.post("/v1/chat/completions", json={**VALID_REQ, "messages": [{"role": "invalid_role", "content": "hi"}]})
        assert r_role.status_code == 400


def test_token_limit_aliases_and_conflict_checks(tmp_path, monkeypatch):
    monkeypatch.delenv("HESCHEMA_API_TOKEN", raising=False)
    with TestClient(create_app(tmp_path / "state.sqlite")) as client:
        # Matching token limits
        r_match = client.post("/v1/chat/completions", json={**VALID_REQ, "max_tokens": 512, "max_completion_tokens": 512})
        assert r_match.status_code == 200

        # Conflicting token limits
        r_conflict = client.post("/v1/chat/completions", json={**VALID_REQ, "max_tokens": 512, "max_completion_tokens": 1024})
        assert r_conflict.status_code == 400
        assert r_conflict.json()["error"]["code"] == "conflicting_parameters"

        # Non-positive limit
        r_neg = client.post("/v1/chat/completions", json={**VALID_REQ, "max_tokens": 0})
        assert r_neg.status_code == 400


def test_prompt_only_mode_strict_rules(tmp_path, monkeypatch):
    monkeypatch.delenv("HESCHEMA_API_TOKEN", raising=False)
    with TestClient(create_app(tmp_path / "state.sqlite")) as client:
        # Prompt-only with strict=true should be rejected
        r_strict = client.post(
            "/v1/chat/completions",
            json={
                **VALID_REQ,
                "heschema_mode": "prompt_only",
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": "schema", "strict": True, "schema": SAMPLE_SCHEMA},
                },
            },
        )
        assert r_strict.status_code == 400
        assert r_strict.json()["error"]["code"] == "strict_mode_unsupported"

        # Prompt-only with strict=false is accepted
        r_ok = client.post(
            "/v1/chat/completions",
            json={
                **VALID_REQ,
                "heschema_mode": "prompt_only",
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": "schema", "strict": False, "schema": SAMPLE_SCHEMA},
                },
            },
        )
        assert r_ok.status_code == 200


def test_schema_dialect_and_reference_rules(tmp_path, monkeypatch):
    monkeypatch.delenv("HESCHEMA_API_TOKEN", raising=False)
    with TestClient(create_app(tmp_path / "state.sqlite")) as client:
        # Unsupported external ref
        ext_ref = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {"other": {"$ref": "https://example.com/schema.json"}},
        }
        r_ext = client.post(
            "/v1/chat/completions",
            json={
                **VALID_REQ,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": "schema", "strict": True, "schema": ext_ref},
                },
            },
        )
        assert r_ext.status_code == 422
        assert r_ext.json()["error"]["code"] == "invalid_schema"

        # Valid local $defs reference
        local_ref = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {"coord": {"$ref": "#/$defs/Point"}},
            "$defs": {"Point": {"type": "object", "properties": {"x": {"type": "integer"}}}},
        }
        r_local = client.post(
            "/v1/chat/completions",
            json={
                **VALID_REQ,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": "schema", "strict": True, "schema": local_ref},
                },
            },
        )
        assert r_local.status_code == 200


def test_auth_enforcement_without_credential_leak(tmp_path, monkeypatch):
    secret_token = "operator-secret-token-xyz"
    monkeypatch.setenv("HESCHEMA_API_TOKEN", secret_token)
    with TestClient(create_app(tmp_path / "state.sqlite")) as client:
        # Missing auth header
        r_no_auth = client.post("/v1/chat/completions", json=VALID_REQ)
        assert r_no_auth.status_code == 401
        assert r_no_auth.json()["error"]["code"] == "invalid_api_key"
        assert secret_token not in r_no_auth.text

        # Invalid token
        r_bad_auth = client.post("/v1/chat/completions", json=VALID_REQ, headers={"Authorization": "Bearer wrong"})
        assert r_bad_auth.status_code == 401
        assert secret_token not in r_bad_auth.text

        # Correct token
        r_good = client.post("/v1/chat/completions", json=VALID_REQ, headers={"Authorization": f"Bearer {secret_token}"})
        assert r_good.status_code == 200


def test_native_ollama_receives_format_and_prompt_only_omits(monkeypatch):
    captured_payloads = []

    def mock_ollama_handler(request: httpx.Request):
        data = json.loads(request.content)
        captured_payloads.append(data)
        return httpx.Response(
            200,
            json={
                "message": {"content": '{"username": "test", "status": "active"}'},
                "prompt_eval_count": 15,
                "eval_count": 8,
                "done": True,
                "done_reason": "stop",
            },
        )

    # 1. Native schema mode
    async def run_native():
        p = Provider("ollama", model="llama3.2:latest", interval=0, transport=httpx.MockTransport(mock_ollama_handler))
        try:
            return await p.generate(
                [{"role": "user", "content": "hi"}],
                format_schema=SAMPLE_SCHEMA,
                retry=False,
            )
        finally:
            await p.close()

    res_native = asyncio.run(run_native())
    assert len(captured_payloads) == 1
    assert captured_payloads[0]["format"] == SAMPLE_SCHEMA
    assert captured_payloads[0]["stream"] is False
    assert res_native.metadata.get("finish_reason") == "stop"

    # 2. Benchmark/default call (no format_schema)
    captured_payloads.clear()

    async def run_default():
        p = Provider("ollama", model="llama3.2:latest", interval=0, transport=httpx.MockTransport(mock_ollama_handler))
        try:
            return await p.generate([{"role": "user", "content": "hi"}], retry=True)
        finally:
            await p.close()

    asyncio.run(run_default())
    assert len(captured_payloads) == 1
    assert "format" not in captured_payloads[0]


def test_diagnostics_separation_and_malformed_json():
    engine = SchemaEngine("jsonschema")
    try:
        # Case 1: Malformed JSON
        malformed = "Not JSON string at all {{"
        d1 = evaluate_document_diagnostics(SAMPLE_SCHEMA, malformed, engine)
        assert d1["jsonParseValid"] is False
        assert d1["heschemaSchemaValid"] is False
        assert d1["semanticCorrectness"] == "Not checked"

        # Case 2: Valid JSON but schema invalid (missing status)
        invalid_json = json.dumps({"username": "alice"})
        d2 = evaluate_document_diagnostics(SAMPLE_SCHEMA, invalid_json, engine)
        assert d2["jsonParseValid"] is True
        assert d2["heschemaSchemaValid"] is False
        assert len(d2["schemaErrors"]) > 0
        assert d2["semanticCorrectness"] == "Not checked"

        # Case 3: Fully conformant JSON
        valid_json = json.dumps({"username": "alice99", "status": "active"})
        d3 = evaluate_document_diagnostics(SAMPLE_SCHEMA, valid_json, engine)
        assert d3["jsonParseValid"] is True
        assert d3["heschemaSchemaValid"] is True
        assert len(d3["schemaErrors"]) == 0
        assert d3["semanticCorrectness"] == "Not checked"
    finally:
        engine.close()


def test_command_previews_redact_secrets():
    previews_no_token = generate_command_previews(
        schema_path="schema.json",
        prompt='Test "quotes"',
        url="http://127.0.0.1:8000/v1/chat/completions",
        model="llama3.2:latest",
        mode="native_schema",
        max_tokens=1024,
        has_token=False,
    )
    assert "--header" not in previews_no_token["posix"]

    previews_with_token = generate_command_previews(
        schema_path="schema.json",
        prompt='Test "quotes"',
        url="http://127.0.0.1:8000/v1/chat/completions",
        model="llama3.2:latest",
        mode="prompt_only",
        max_tokens=1024,
        has_token=True,
    )
    assert "$HESCHEMA_API_TOKEN" in previews_with_token["posix"]
    assert "$env:HESCHEMA_API_TOKEN" in previews_with_token["powershell"]
    assert "--param /heschema_mode=prompt_only" in previews_with_token["posix"]
    assert "--param /response_format/json_schema/strict=false" in previews_with_token["posix"]


def test_cli_integration_lab_endpoints(tmp_path, monkeypatch):
    monkeypatch.delenv("HESCHEMA_API_TOKEN", raising=False)
    with TestClient(create_app(tmp_path / "state.sqlite")) as client:
        # GET /ui/cli-integration/status
        status_res = client.get("/ui/cli-integration/status")
        assert status_res.status_code == 200
        data = status_res.json()
        assert "cli" in data and "ollama" in data and "loopbackUrl" in data
        assert "required_string" in data["presets"]

        # POST /ui/cli-integration/validate
        val_res = client.post(
            "/ui/cli-integration/validate",
            json={
                "schema": SAMPLE_SCHEMA,
                "output": json.dumps({"username": "alice", "status": "active"}),
            },
        )
        assert val_res.status_code == 200
        assert val_res.json()["heschemaSchemaValid"] is True
        assert val_res.json()["semanticCorrectness"] == "Not checked"


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class FakeOllamaHandler(BaseHTTPRequestHandler):
    scenario = "valid"

    def do_GET(self):
        if self.path == "/api/tags":
            body = json.dumps({"models": [{"name": "fake-ollama-model:latest"}]}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length)
        payload = json.loads(body_bytes.decode("utf-8"))

        # Verify that native schema format was forwarded to Ollama
        assert "format" in payload
        assert payload["stream"] is False

        if FakeOllamaHandler.scenario == "valid":
            out_json = json.dumps({"username": "alice99", "status": "active"})
        elif FakeOllamaHandler.scenario == "schema_invalid":
            # Missing required field 'status'
            out_json = json.dumps({"username": "alice99"})
        else:
            # Malformed JSON
            out_json = "malformed not json {{"

        response_body = json.dumps({
            "message": {"content": out_json},
            "prompt_eval_count": 20,
            "eval_count": 10,
            "done": True,
            "done_reason": "stop",
        }).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(response_body)

    def log_message(self, format, *args):
        pass  # Quiet logging


def test_real_cli_interoperability_with_uvicorn_and_fake_ollama(tmp_path, monkeypatch):
    """End-to-end protocol interoperability test with real Sourcemeta CLI against single-worker Uvicorn."""
    cmd_prefix, resolved_target = resolve_cli_path()
    cli_probe = asyncio.run(probe_cli_support())
    if not cli_probe["available"] or not cli_probe["llm_supported"]:
        pytest.skip(f"Sourcemeta CLI llm capability not available on this host: {cli_probe['message']}")

    # 1. Start Fake Ollama server on free port
    ollama_port = get_free_port()
    ollama_server = HTTPServer(("127.0.0.1", ollama_port), FakeOllamaHandler)
    ollama_thread = threading.Thread(target=ollama_server.serve_forever, daemon=True)
    ollama_thread.start()

    # 2. Configure HESchema loopback and provider port
    app_port = get_free_port()
    loopback_url = f"http://127.0.0.1:{app_port}/v1/chat/completions"
    monkeypatch.setenv("OLLAMA_BASE_URL", f"http://127.0.0.1:{ollama_port}")
    monkeypatch.setenv("HESCHEMA_PORT", str(app_port))
    monkeypatch.setenv("HESCHEMA_LOOPBACK_URL", loopback_url)
    monkeypatch.delenv("HESCHEMA_API_TOKEN", raising=False)

    app = create_app(tmp_path / "state.sqlite")
    config = uvicorn.Config(app, host="127.0.0.1", port=app_port, log_level="error")
    server = uvicorn.Server(config)
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    # Wait for server to become responsive
    time.sleep(1.0)

    try:
        # Schema temp file
        schema_file = tmp_path / "test_interop_schema.json"
        schema_file.write_text(json.dumps(SAMPLE_SCHEMA), encoding="utf-8")

        # Test Case 1: Valid scenario
        FakeOllamaHandler.scenario = "valid"
        argv_valid = list(cmd_prefix) + [
            "llm",
            str(schema_file),
            "--ask",
            "Generate alice99 user profile",
            "--url",
            loopback_url,
            "--model",
            "fake-ollama-model:latest",
            "--json",
            "--timeout",
            "15",
        ]

        async def run_valid():
            proc = await asyncio.create_subprocess_exec(
                *argv_valid,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=20.0)
            return proc.returncode, stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")

        exit_code, out_str, err_str = asyncio.run(run_valid())
        assert exit_code == 0, f"Expected CLI exit 0, got {exit_code}. stderr: {err_str}"
        parsed = json.loads(out_str)
        doc = parsed.get("document", parsed)
        assert doc.get("username") == "alice99"
        assert doc.get("status") == "active"
        if "output" in parsed:
            assert parsed["output"].get("valid") is True

        # Test Case 2: Schema-invalid scenario (missing required field)
        FakeOllamaHandler.scenario = "schema_invalid"
        async def run_invalid():
            proc = await asyncio.create_subprocess_exec(
                *argv_valid,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=20.0)
            return proc.returncode, stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")

        exit_code_inv, out_str_inv, err_str_inv = asyncio.run(run_invalid())
        # Sourcemeta CLI must reject the schema-invalid instance with non-zero exit code
        assert exit_code_inv != 0, f"Expected non-zero exit code for schema invalid response, but got {exit_code_inv}"

    finally:
        server.should_exit = True
        ollama_server.shutdown()
        ollama_server.server_close()
