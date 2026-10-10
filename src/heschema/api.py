"""Local FastAPI service. PASS is a validation decision, never an execution permit."""

import os
import secrets
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .benchmark import ARMS, messages_for
from .domains import DOMAINS, reference_schema
from .jobs import JobConflictError, JobManager
from .jsonio import canonical, loads
from .providers import ROOT, Provider, ProviderError, registry, tavily_search
from .schema import SchemaEngine, check_schema, typed_minimal
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
    schemaMode: str | None = None


class ExtractBody(Body):
    prompt: str = Field(min_length=1, max_length=20000)
    domain: str
    provider: str
    model: str | None = None


class SearchBody(Body):
    query: str = Field(min_length=1, max_length=2000)
    maxResults: int = Field(default=5, ge=1, le=10)


class PromptTestBody(Body):
    prompt: str = Field(min_length=1, max_length=20000)
    domain: str
    provider: str
    model: str | None = None
    schemaMode: str = Field(default="supplied_schema")  # "no_schema" | "supplied_schema"
    schema_: dict[str, Any] | bool | None = Field(default=None, alias="schema")
    stateId: str | None = None
    stateVersion: int | None = None


class PromptCompareBody(Body):
    prompt: str = Field(min_length=1, max_length=20000)
    domain: str
    provider: str
    model: str | None = None
    stateId: str
    stateVersion: int = Field(ge=1)
    schema_: dict[str, Any] | bool | None = Field(default=None, alias="schema")
    repeats: int = Field(default=1, ge=1, le=5)


class SchemaValidateBody(Body):
    schema_: dict[str, Any] | bool = Field(alias="schema")
    domain: str | None = None


class BenchmarkJobBody(Body):
    domain: str
    provider: str
    model: str | None = None
    preset: str = Field(default="quick")
    caseCount: int | None = None
    repeats: int = Field(default=1, ge=1, le=5)
    repairs: int = Field(default=0, ge=0, le=5)
    interval: float | None = None
    seed: int = 42
    schema_: dict[str, Any] | bool | None = Field(default=None, alias="schema")
    inputPrice: float | None = None
    outputPrice: float | None = None


EXAMPLES = {
    "flights": {
        "prompt": "Find flights from Jaipur to Goa on 2027-01-20 for 2 travellers.",
        "state": {
            "origin": "Jaipur",
            "destination": "Goa",
            "departureDate": "2027-01-20",
            "travellers": 2,
        },
        "description": "Flight search request with complete required details.",
    },
    "hotels": {
        "prompt": "Search hotel in Goa checking in on 2027-01-10 and checking out on 2027-01-15 for 2 guests with max nightly price 5000.",
        "state": {
            "city": "Goa",
            "checkIn": "2027-01-10",
            "checkOut": "2027-01-15",
            "guests": 2,
            "maxNightlyPrice": 5000,
        },
        "description": "Hotel search adhering to checkIn < checkOut policy.",
    },
    "calendar": {
        "prompt": "Prepare event Project review 1 on 2027-01-15 at 10:30 for 60 minutes in Room 101.",
        "state": {
            "title": "Project review 1",
            "date": "2027-01-15",
            "startTime": "10:30",
            "durationMinutes": 60,
            "venue": "Room 101",
        },
        "description": "Calendar event draft meeting pattern.",
    },
    "payments": {
        "prompt": "Prepare transfer of 75050 minor units (750.50 INR) to account-1001 with reference invoice-101.",
        "state": {
            "recipient": "account-1001",
            "amountMinor": 75050,
            "currency": "INR",
            "reference": "invoice-101",
        },
        "description": "Payment quote respecting integer minor units (amountMinor <= 100000).",
    },
    "inventory": {
        "prompt": "Reserve stock draft of 15 units for SKU-101 at warehouse DEL with orderId order-501.",
        "state": {
            "sku": "SKU-101",
            "warehouse": "DEL",
            "quantity": 15,
            "orderId": "order-501",
        },
        "description": "Stock reservation quote (quantity <= 50).",
    },
    "search": {
        "prompt": "Search web for JSON Schema documentation with max 5 results under general topic.",
        "state": {
            "query": "JSON Schema documentation",
            "maxResults": 5,
            "topic": "general",
        },
        "description": "Web search query specification.",
    },
}


def create_app(db_path=None):
    load_dotenv(ROOT / ".env", override=False)
    store = StateStore(db_path or os.getenv("HESCHEMA_DB", str(ROOT / "data/state.sqlite3")))
    engine = SchemaEngine(os.getenv("HESCHEMA_ENGINE", "jsonschema"))
    job_manager = JobManager()

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
            parsed = loads(result.text)
            if engine.errors(ENVELOPE, parsed):
                raise HTTPException(422, "Model proposal has an invalid output envelope")
            if parsed.get("action") != "call_tool":
                action = parsed.get("action")
                reason = parsed.get("reason", "")
                missing = parsed.get("missingFields", [])
                notice = f"Model chose '{action}': {reason}"
                if missing:
                    notice += f" (Missing: {', '.join(missing)})"
                return {"proposal": parsed, "state": None, "confirmed": False, "notice": notice}
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
        snapshot(body.stateId, identity, body.stateVersion)
        result["stateVersion"] = body.stateVersion
        return runtime_gate(result)

    @app.post("/generate")
    async def generate(body: GenerateBody, identity=Depends(owner)):
        snap = snapshot(body.stateId, identity, body.stateVersion)
        spec, ref = domain_spec(body.domain)
        validate_state(ref, snap)
        if body.schemaMode == "no_schema":
            generation_schema = None
            candidate = ref
        else:
            candidate = body.schema_ if body.schema_ is not None else ref
            engine.register(candidate)
            generation_schema = candidate

        try:
            provider = Provider(body.provider, body.model)
            try:
                case = {"domain": body.domain, "prompt": snap["prompt"],
                        "context": {"confirmedState": snap["state"], "stateVersion": snap["version"]}}
                generated = await provider.generate(messages_for(case, generation_schema))
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

    # --- Web UI Routes ---

    @app.get("/ui/examples/{domain}")
    def get_example(domain: str, identity=Depends(owner)):
        if domain not in EXAMPLES:
            raise HTTPException(422, "Unknown domain")
        return EXAMPLES[domain]

    @app.post("/ui/validate-schema")
    def validate_schema_endpoint(body: SchemaValidateBody, identity=Depends(owner)):
        try:
            check_schema(body.schema_)
            return {"valid": True, "error": None}
        except ValueError as exc:
            return {"valid": False, "error": str(exc)}

    @app.post("/ui/prompt-test")
    async def prompt_test(body: PromptTestBody, identity=Depends(owner)):
        spec, ref = domain_spec(body.domain)
        snap = None
        state = None
        if body.stateId:
            try:
                snap = store.get(body.stateId, identity)
                if body.stateVersion is not None and snap["version"] != body.stateVersion:
                    raise HTTPException(409, "Stale state version")
                if snap["confirmed"]:
                    state = snap["state"]
            except KeyError:
                raise HTTPException(404, "State not found") from None

        if body.schemaMode == "no_schema":
            generation_schema = None
            candidate = ref
        else:
            candidate = body.schema_ if body.schema_ is not None else ref
            try:
                check_schema(candidate)
                engine.register(candidate)
            except ValueError as exc:
                raise HTTPException(422, f"Invalid schema: {exc}") from None
            generation_schema = candidate

        try:
            provider = Provider(body.provider, body.model)
            case = {"domain": body.domain, "prompt": body.prompt}
            if snap and snap["confirmed"]:
                case["context"] = {"confirmedState": snap["state"], "stateVersion": snap["version"]}
            try:
                generated = await provider.generate(messages_for(case, generation_schema))
            finally:
                await provider.close()

            raw_text = generated.text
            parsed = None
            try:
                parsed = loads(raw_text)
            except Exception:
                pass

            if state is not None:
                expected = envelope("call_tool", spec["tool"], state)
                val_res = evaluate(raw_text, engine, ref, candidate, expected, state=state, policy=spec.get("policy", {}))
                val_res["semanticChecked"] = True
                val_res = runtime_gate(val_res)
            else:
                expected_action = parsed.get("action", "call_tool") if parsed else "call_tool"
                expected_tool = spec["tool"] if expected_action == "call_tool" else None
                expected_missing = parsed.get("missingFields", []) if parsed else []
                expected = envelope(expected_action, tool=expected_tool, arguments=None, missing=expected_missing)
                val_res = evaluate(raw_text, engine, ref, candidate, expected, state=None, policy=spec.get("policy", {}))
                val_res["semanticValid"] = None
                val_res["semanticChecked"] = False
                val_res["benchmarkSuccess"] = False
                val_res["success"] = False
                if not val_res["jsonValid"] or not val_res["referenceSchemaValid"] or not val_res["policyValid"] or not val_res["candidateSchemaValid"]:
                    val_res["result"] = "FAIL"
                else:
                    val_res["result"] = "NOT_CHECKED"
                val_res["notice"] = "Semantic correctness not checked: confirm an actual state to verify agreement."

            return {
                "model": generated.model,
                "output": raw_text,
                "parsed": parsed,
                "validation": val_res,
                "latencyMs": generated.latency_ms,
                "hasConfirmedState": state is not None,
                "stateVersion": snap["version"] if snap else None
            }
        except (ProviderError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from None

    @app.post("/ui/prompt-compare")
    async def prompt_compare(body: PromptCompareBody, identity=Depends(owner)):
        snap = snapshot(body.stateId, identity, body.stateVersion)
        spec, ref = domain_spec(body.domain)
        validate_state(ref, snap)
        candidate = body.schema_ if body.schema_ is not None else ref
        check_schema(candidate)
        engine.register(candidate)
        min_schema = typed_minimal(ref)
        engine.register(min_schema)

        arms_schema = {
            "no_schema": None,
            "minimal_schema": min_schema,
            "input_schema": candidate
        }

        try:
            provider = Provider(body.provider, body.model)
            results_by_arm = {}
            case = {"domain": body.domain, "prompt": body.prompt,
                    "context": {"confirmedState": snap["state"], "stateVersion": snap["version"]}}
            expected = envelope("call_tool", spec["tool"], snap["state"])

            try:
                for arm in ARMS:
                    arm_runs = []
                    shown = arms_schema[arm]
                    messages = messages_for(case, shown)
                    for rep in range(body.repeats):
                        gen = await provider.generate(messages)
                        eval_res = evaluate(gen.text, engine, ref, candidate, expected,
                                            state=snap["state"], policy=spec.get("policy", {}))
                        runtime_gate(eval_res)
                        arm_runs.append({
                            "repeat": rep,
                            "output": gen.text,
                            "parsed": eval_res.get("parsed"),
                            "latencyMs": gen.latency_ms,
                            "firstPassSuccess": eval_res["success"],
                            "evaluation": eval_res
                        })
                    success_count = sum(1 for r in arm_runs if r["firstPassSuccess"])
                    results_by_arm[arm] = {
                        "runs": arm_runs,
                        "successCount": success_count,
                        "successPercent": (success_count / body.repeats) * 100 if body.repeats else 0,
                        "meanLatencyMs": sum(r["latencyMs"] for r in arm_runs) / len(arm_runs) if arm_runs else 0
                    }
            finally:
                await provider.close()

            return {
                "trialType": "Single-prompt trial",
                "notice": "Single-prompt trial results show observed outcomes for this specific prompt and must not be interpreted as a domain-wide schema effect.",
                "domain": body.domain,
                "model": body.model,
                "repeats": body.repeats,
                "arms": results_by_arm
            }
        except (ProviderError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from None

    @app.post("/ui/jobs")
    async def create_job(body: BenchmarkJobBody, identity=Depends(owner)):
        try:
            record = await job_manager.create_benchmark_job(
                domain=body.domain,
                provider_name=body.provider,
                model=body.model,
                schema=body.schema_,
                preset=body.preset,
                case_count=body.caseCount,
                repeats=body.repeats,
                repairs=body.repairs,
                interval=body.interval,
                seed=body.seed,
                input_price=body.inputPrice,
                output_price=body.outputPrice,
                operator=identity
            )
            return record.public_dict()
        except JobConflictError as exc:
            raise HTTPException(409, str(exc)) from None
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @app.get("/ui/jobs/{job_id}")
    def get_job_status(job_id: str, identity=Depends(owner)):
        try:
            return job_manager.get_job(job_id, identity).public_dict()
        except KeyError:
            raise HTTPException(404, "Job not found") from None

    @app.post("/ui/jobs/{job_id}/cancel")
    def cancel_job(job_id: str, identity=Depends(owner)):
        try:
            return job_manager.cancel_job(job_id, identity).public_dict()
        except KeyError:
            raise HTTPException(404, "Job not found") from None

    @app.get("/ui/jobs/{job_id}/report")
    def get_job_report(job_id: str, identity=Depends(owner)):
        try:
            return job_manager.get_report(job_id, identity)
        except KeyError:
            raise HTTPException(404, "Job not found") from None
        except FileNotFoundError:
            raise HTTPException(404, "Report not yet available") from None

    @app.get("/ui/jobs/{job_id}/report/markdown")
    def get_job_markdown(job_id: str, identity=Depends(owner)):
        try:
            content = job_manager.get_markdown_report(job_id, identity)
            return PlainTextResponse(content, media_type="text/markdown")
        except KeyError:
            raise HTTPException(404, "Job not found") from None
        except FileNotFoundError:
            raise HTTPException(404, "Report not yet available") from None

    @app.get("/ui/jobs/{job_id}/runs")
    def get_job_runs(job_id: str, offset: int = 0, limit: int = 100, identity=Depends(owner)):
        try:
            return job_manager.get_runs(job_id, identity, offset=offset, limit=limit)
        except KeyError:
            raise HTTPException(404, "Job not found") from None

    # --- Static UI Mount ---
    frontend_dir = ROOT / "frontend"
    if frontend_dir.exists():
        app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

        @app.get("/", response_class=FileResponse)
        def index():
            return FileResponse(frontend_dir / "index.html")

    return app
