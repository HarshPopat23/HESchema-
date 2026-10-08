"""Local FastAPI service. PASS is a validation decision, never an execution permit."""

import os
import secrets
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from .benchmark import messages_for
from .domains import DOMAINS, reference_schema
from .providers import ROOT, Provider, ProviderError, registry, tavily_search
from .schema import SchemaEngine
from .state import StateStore
from .validation import ENVELOPE, envelope, evaluate


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StateBody(Body):
    prompt: str = Field(min_length=1, max_length=20000)
    state: dict[str, Any]


class ConfirmBody(Body):
    version: int = Field(ge=1)


class ReplaceBody(ConfirmBody):
    state: dict[str, Any]


class ValidateBody(Body):
    stateId: str
    stateVersion: int = Field(ge=1)
    domain: str
    output: str | dict[str, Any]
    schema_: dict[str, Any] | bool | None = Field(default=None, alias="schema")


class GenerateBody(Body):
    stateId: str
    stateVersion: int = Field(ge=1)
    domain: str
    provider: str
    model: str | None = None
    schema_: dict[str, Any] | bool | None = Field(default=None, alias="schema")


class ExtractBody(Body):
    prompt: str = Field(min_length=1, max_length=20000)
    domain: str
    provider: str
    model: str | None = None


class SearchBody(Body):
    query: str = Field(min_length=1, max_length=2000)
    maxResults: int = Field(default=5, ge=1, le=10)


def create_app(db_path=None):
    load_dotenv(ROOT / ".env", override=False)
    store = StateStore(db_path or os.getenv("HESCHEMA_DB", str(ROOT / "data/state.sqlite3")))
    engine = SchemaEngine(os.getenv("HESCHEMA_ENGINE", "jsonschema"))

    @asynccontextmanager
    async def lifespan(app):
        yield
        engine.close()

    app = FastAPI(title="HESchema", version="0.1.0", lifespan=lifespan)

    bearer = HTTPBearer(auto_error=False)

    def owner(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        token = os.getenv("HESCHEMA_API_TOKEN", "")
        if token:
            if not credentials or not secrets.compare_digest(credentials.credentials, token):
                raise HTTPException(401, "Invalid API token")
            # Single backend operator. Multi-user auth requires a trusted identity
            # provider; never accept a caller-supplied owner header as authentication.
            return "operator"
        return "local-operator"

    def snapshot(state_id, identity, version):
        try:
            snap = store.get(state_id, identity)
        except KeyError:
            raise HTTPException(404, "State not found") from None
        if snap["version"] != version:
            raise HTTPException(409, "Stale state version")
        if not snap["confirmed"]:
            raise HTTPException(409, "Confirm state before generating or validating tool calls")
        return snap

    def domain_spec(domain):
        if domain not in DOMAINS:
            raise HTTPException(422, "Unknown domain")
        return DOMAINS[domain], reference_schema(domain)

    def validate_state(ref, snap):
        errs = engine.errors(ref, snap["state"])
        if errs:
            raise HTTPException(422, {"message": "Confirmed state violates reference contract", "errors": errs})

    def runtime_gate(result):
        # Benchmark success uses a fixed reference judge across arms. Runtime
        # additionally requires compliance with the operator's supplied schema.
        result["benchmarkSuccess"] = result["success"]
        result["success"] = result["success"] and result["candidateSchemaValid"]
        result["result"] = "PASS" if result["success"] else "FAIL"
        return result

    @app.get("/health")
    def health():
        return {"status": "ok", "engine": engine.backend, "executionEnabled": False}

    @app.get("/providers")
    def providers(identity=Depends(owner)):
        return registry()

    @app.get("/schemas/{domain}")
    def schema(domain: str, identity=Depends(owner)):
        _, ref = domain_spec(domain)
        return ref

    @app.post("/states")
    def create_state(body: StateBody, identity=Depends(owner)):
        return store.create(identity, body.prompt, body.state)

    @app.get("/states/{state_id}")
    def get_state(state_id: str, identity=Depends(owner)):
        try:
            return store.get(state_id, identity)
        except KeyError:
            raise HTTPException(404, "State not found") from None

    @app.post("/states/{state_id}/confirm")
    def confirm(state_id: str, body: ConfirmBody, identity=Depends(owner)):
        try:
            return store.confirm(state_id, identity, body.version)
        except ValueError:
            raise HTTPException(409, "Stale state version or unknown state") from None

    @app.put("/states/{state_id}")
    def replace(state_id: str, body: ReplaceBody, identity=Depends(owner)):
        try:
            return store.replace(state_id, identity, body.version, body.state)
        except ValueError:
            raise HTTPException(409, "Stale state version or unknown state") from None

    @app.post("/extract")
    async def extract(body: ExtractBody, identity=Depends(owner)):
        spec, ref = domain_spec(body.domain)
        case = {"domain": body.domain, "prompt": body.prompt}
        try:
            provider = Provider(body.provider, body.model)
            try:
                result = await provider.generate(messages_for(case, ref))
            finally:
                await provider.close()
            from .jsonio import loads
            parsed = loads(result.text)
            if engine.errors(ENVELOPE, parsed):
                raise HTTPException(422, "Model proposal has an invalid output envelope")
            if parsed.get("action") != "call_tool":
                return {"proposal": parsed, "state": None, "confirmed": False}
            if parsed.get("tool") != spec["tool"] or engine.errors(ref, parsed.get("arguments")):
                raise HTTPException(422, "Model proposal is structurally invalid")
            snap = store.create(identity, body.prompt, parsed["arguments"])
            return {"proposal": parsed, "state": snap, "confirmed": False,
                    "notice": "User must verify values before confirmation; extraction can be wrong"}
        except (ProviderError, ValueError, TypeError, AttributeError) as exc:
            raise HTTPException(422, str(exc)) from None

    @app.post("/validate")
    def validate(body: ValidateBody, identity=Depends(owner)):
        snap = snapshot(body.stateId, identity, body.stateVersion)
        spec, ref = domain_spec(body.domain)
        validate_state(ref, snap)
        candidate = body.schema_ if body.schema_ is not None else ref
        try:
            result = evaluate(body.output, engine, ref, candidate,
                              envelope("call_tool", spec["tool"], snap["state"]),
                              snap["state"], spec.get("policy", {}))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        # Version recheck detects concurrent changes during validation. Since this
        # service never executes the operation, no validate/execute race is hidden.
        snapshot(body.stateId, identity, body.stateVersion)
        result["stateVersion"] = body.stateVersion
        return runtime_gate(result)

    @app.post("/generate")
    async def generate(body: GenerateBody, identity=Depends(owner)):
        snap = snapshot(body.stateId, identity, body.stateVersion)
        spec, ref = domain_spec(body.domain)
        validate_state(ref, snap)
        candidate = body.schema_ if body.schema_ is not None else ref
        try:
            engine.register(candidate)
            provider = Provider(body.provider, body.model)
            try:
                case = {"domain": body.domain, "prompt": snap["prompt"],
                        "context": {"confirmedState": snap["state"], "stateVersion": snap["version"]}}
                generated = await provider.generate(messages_for(case, candidate))
            finally:
                await provider.close()
            result = evaluate(generated.text, engine, ref, candidate,
                              envelope("call_tool", spec["tool"], snap["state"]), snap["state"], spec.get("policy", {}))
            snapshot(body.stateId, identity, body.stateVersion)
            return {"model": generated.model, "output": generated.text, "validation": runtime_gate(result),
                    "latencyMs": generated.latency_ms, "stateVersion": snap["version"]}
        except (ProviderError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from None

    @app.post("/integrations/tavily/search")
    async def search(body: SearchBody, identity=Depends(owner)):
        try:
            return await tavily_search(body.query, body.maxResults)
        except ProviderError as exc:
            raise HTTPException(502, str(exc)) from None

    return app
