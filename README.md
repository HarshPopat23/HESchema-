# HESchema

A runnable **schema-effect experiment harness + state-aware tool-argument validator**. It answers two different questions:

1. **“Is this specific LLM-generated argument safe and correct?”** Check strict JSON, the tool contract, a user-confirmed state snapshot, and declared application policies. Return `PASS` or `FAIL`, with reasons.
2. **“How much does this JSON Schema improve or harm this model on this task domain?”** Run the same tasks through no-schema, minimal-schema, and supplied-schema arms. Compare first-pass correct-and-valid success with paired statistics, retries, usage, cost, and latency.

**Important:** `PASS` means the implemented checks passed. It is not universal safety certification, proof that an extracted state is true, or permission to book/pay. This project never executes flight bookings, payments, calendar writes, or inventory changes.

## What's included

- **480 distinct, reproducible synthetic benchmark cases**: six domains × 80 tasks, with hidden evaluation oracles.
- **36 schema fixtures**: reference, minimal, rich, weak, contradictory, and complex-but-equivalent for each domain.
- Strict Draft 2020-12 schema checking, date-format assertions, bounded evaluator caches, and compiled immutable state bindings.
- Optional **Sourcemeta Blaze compilation/evaluation integration**: native CLI compiles templates; a persistent JavaScript worker evaluates them. Python independently checks results and formats.
- SQLite-backed confirmed/versioned state; stale-state and ownership checks; extraction remains an unconfirmed proposal.
- OpenAI, Anthropic, Groq, Mistral, Gemini, OpenRouter, Hugging Face, Ollama, and offline mock adapters.
- **Tavily search integration**, separately from LLM scoring. Tavily is a search API, not a language model.
- Paired clustered-bootstrap confidence intervals, guarded relative uplift/error reduction, exact McNemar where applicable, mutation probes, descriptive classifications, and cross-model comparison.
- Resumable JSONL experiment logs, JSON/Markdown reports, API/OpenAPI docs, automated tests, and GitHub CI.

This is an evaluation prototype, not a new general-purpose optimizing compiler. It integrates Blaze rather than claiming to recreate its performance. **There is no measured 10× speed or LLM-improvement claim in this repository.**

## Quick start

Python 3.11+; run from this repository checkout. Installation is editable because schemas, provider configuration, and the optional native worker live beside the source.

```bash
git clone https://github.com/HarshPopat23/HESchema-.git
cd HESchema-
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
heschema dataset
pytest -q
heschema benchmark --provider mock --repeats 1 --repairs 0 --out results/offline
heschema serve
```

Windows can use `.venv\Scripts\activate`; the default Python validator works there. The optional Blaze worker uses a POSIX pipe timeout.

Open http://127.0.0.1:8000/docs for interactive API documentation, or `/openapi.json` for the machine-readable OpenAPI document. **The mock run is only a pipeline test:** it always returns a fixed refusal, does not consult gold answers, and cannot establish real LLM improvement. Its reports mark `empiricalLLMEvidence: false` and `comparisonValid: false`.

## Web UI

A simple, dependency-free local web UI is served directly through FastAPI.

### Launch command
```bash
python -m heschema.cli serve --port 8000
```
Open **http://127.0.0.1:8000/** in your browser. API docs remain at **http://127.0.0.1:8000/docs**.

### Workflows supported
1. **Prompt-test workflow**:
   - Enter a prompt, select a provider and model, and choose generation mode (*With argument schema* or *Without argument schema*).
   - Inspect raw model output, parsed tool arguments, envelope conformance, Draft 2020-12 schema validation, and declared domain policies.
   - Without confirmed state, semantic correctness is displayed as **Not checked**; a complete correctness `PASS` is never reported without ground truth.
2. **State-confirmation workflow**:
   - Click **Extract Proposed State** to propose state from the prompt.
   - An LLM extraction is only a proposal: review values in the editor and click **Confirm Actual State**.
   - Editing values removes confirmation; stale versions are visibly rejected (HTTP 409).
   - Confirmed state enforces strict parameter binding: if confirmed destination is `Goa` and generated destination is `Pune`, validation fails with `STATE_MISMATCH`.
3. **Single-prompt comparison**:
   - Click **Compare Three Arms** on a confirmed state to evaluate `no_schema`, `minimal_schema`, and `input_schema` on that prompt.
   - **Limits of single-prompt percentages**: Labeled *Single-prompt trial*. It reflects only that specific prompt and cannot claim a domain-wide schema effect.
4. **Schema-benchmark workflow**:
   - Select Quick Test (14 cases across all 7 categories = 42 calls) or Full Domain (80 cases = 720 calls), or configure custom cases, repeats, repairs, interval, and token prices.
   - Run in the background with live progress tracking (completed runs, requests attempted, provider errors) and graceful cancellation.
   - Inspect 3-arm comparison tables, paired uplift, and 95% clustered bootstrap intervals.
   - Scientific conclusions apply: an interval crossing zero is strictly reported as **Inconclusive**.
   - **Report storage**: Results are stored in `results/jobs/<jobId>/` (`report.json`, `report.md`, and `runs.jsonl`), with direct download buttons in the UI.
5. **CLI-integration workflow (Sourcemeta JSON Schema CLI)**:
   - **Tab:** *CLI Integration* ("Test a local OpenAI-compatible endpoint with Sourcemeta's JSON Schema CLI.").
   - **Local OpenAI-Compatible Completion Endpoint:** `POST /v1/chat/completions` accepting standard OpenAI structured output payloads (`response_format.type = "json_schema"`).
   - **Generation Modes:**
     - `native_schema` (default): sends accepted JSON Schema directly to Ollama's `format` object for constrained decoding.
     - `prompt_only` (comparison): grounds schema constraints in message prompt and omits native Ollama format enforcement (requires `strict: false`).
   - **Real Sourcemeta CLI Execution:** Invokes `@sourcemeta/jsonschema` (`llm` command) via asynchronous child subprocess against the loopback `/v1/chat/completions` endpoint without blocking single-worker Uvicorn.
   - **5 Presets Included:** Required string & `additionalProperties: false`, enum & integer bounds, nested objects & bounded array, oneOf conditional, and local `$defs`/`$ref`.
   - **Independent Diagnostics:** Evaluates HTTP transport success, strict JSON parsing (`jsonio.loads`), schema conformance, and CLI process reports separately; semantic correctness is strictly reported as **Not checked** for arbitrary schemas without ground truth.
   - **Reproducible Command Previews:** Shows copy-pasteable Bash and PowerShell commands with `$HESCHEMA_API_TOKEN` placeholders.

For a real run, add the relevant backend API key to `.env`. Do not commit keys. Start with a small request budget:

```bash
heschema providers
heschema benchmark --provider groq --domain flights \
  --schema benchmarks/schemas/flights.rich.json \
  --repeats 3 --repairs 2 --interval 4 \
  --max-requests 60 --out results/groq-flights-rich
```

Repeat the **same command/output directory** to resume. Completed task/arm/repetition rows with a usable provider response are not rerun; provider-error rows can be retried on resume. The append-only log retains history, while reports use the latest row per logical run. Three consecutive provider errors stop the invocation to avoid hammering an unavailable service. Configuration changes require a new directory. A cap reserves the worst-case remaining repair calls before starting each row, so it can stop below the cap. Provider-internal HTTP retries are additional and tracked separately. This is a request cap, not a monetary guarantee.

When ready, omit `--max-requests` to finish all pairs. Partial reports are explicitly flagged and should not be interpreted as complete comparisons. `--limit` selects the first N cases, which can be category-skewed; use it for smoke tests, not representative conclusions.

## Models and services

| Provider | Example configured model | Credentials | Free/low-cost caveat |
|---|---|---|---|
| Groq | `openai/gpt-oss-20b` | `GROQ_API_KEY` | Free developer quotas depend on account/model; not unlimited |
| Mistral | `mistral-small-latest` | `MISTRAL_API_KEY` | Experiment/free access can have restrictions; verify your account |
| Gemini | `gemini-2.5-flash` | `GEMINI_API_KEY` | Free-tier eligibility and limits vary |
| OpenRouter | `openrouter/free` | `OPENROUTER_API_KEY` | Free routing may change the underlying model; prefer a fixed model for experiments |
| Hugging Face | `Qwen/Qwen3-8B` | `HF_TOKEN` | Credits/provider availability vary; not an unlimited free API |
| Ollama | `qwen3:4b-instruct` | Local daemon | No hosted API fee; hardware/electricity still cost money |
| OpenAI | `gpt-6-luna` | `OPENAI_API_KEY` | Normally paid API usage; account availability varies |
| Anthropic | `claude-haiku-4-5` | `ANTHROPIC_API_KEY` | Normally paid API usage; account availability varies |
| Mock | `offline-stub` | None | Offline testing only, never empirical evidence |
| Tavily | Search, not an LLM | `TAVILY_API_KEY` | Separate search quota/billing; not part of the schema experiment |

These are editable examples, **not a promise that every model is available to every account**. Override with `--model YOUR_MODEL_ID`. Provider configuration is in [`config/providers.json`](config/providers.json). Free-tier/model availability changes. The adapters omit temperature unless requested because some models do not accept it. Seeds are sent only for configured providers that support them; reproducible schedules do not guarantee deterministic hosted generation.

For local inference, start Ollama and pull a model:

```bash
ollama pull qwen3:4b-instruct
heschema benchmark --provider ollama --model qwen3:4b-instruct \
  --domain flights --repeats 3 --interval 0 --out results/ollama-flights
```

## Workflow 1: validate a specific argument

1. The host receives the user prompt, constructs context, and selects the tool/domain/model.
2. A form or `/extract` proposes actual state. **An LLM extraction is not ground truth.** The user must inspect values before `/confirm`.
3. SQLite stores a confirmed snapshot and version. Editing increments the version and removes confirmation.
4. `/generate` supplies the prompt, confirmed context, tool information, and argument schema to the selected model.
5. The model returns an envelope containing **tool arguments**, not a newly generated schema.
6. The service checks JSON/envelope, candidate schema, reference contract, confirmed state bindings, tool/action, and declared policies. It rechecks the state version before returning.
7. Return `PASS/FAIL`, errors, and `executionAuthorized: false`. A separate executor would need authentication, transaction-time version checks, idempotency, and explicit authorization before any real action.

For example, confirmed `destination = Goa` and generated `destination = Pune` produce `referenceSchemaValid: true`, `semanticValid: false`, and `FAIL`. JSON Schema can constrain types and bounds, but it cannot inherently know the user's chosen destination. State-aware checks supply that knowledge.

### Try the API

```bash
curl -s http://127.0.0.1:8000/states -H 'Content-Type: application/json' -d '{
  "prompt":"Find flights from Jaipur to Goa on 2027-01-01 for one traveller",
  "state":{"origin":"Jaipur","destination":"Goa","departureDate":"2027-01-01","travellers":1}
}'
```

Copy the returned `id`; inspect the state and then confirm:

```bash
curl -s http://127.0.0.1:8000/states/STATE_ID/confirm \
  -H 'Content-Type: application/json' -d '{"version":1}'
curl -s http://127.0.0.1:8000/validate -H 'Content-Type: application/json' -d '{
  "stateId":"STATE_ID","stateVersion":1,"domain":"flights",
  "output":{"action":"call_tool","tool":"search_flights",
    "arguments":{"origin":"Jaipur","destination":"Pune","departureDate":"2027-01-01","travellers":1},
    "missingFields":[],"reason":"Flight search"}
}'
```

This returns `FAIL`. Replace Pune with Goa to pass the declared checks. `/generate` accepts `stateId`, `stateVersion`, `domain`, `provider`, and optionally `model` and `schema`. `/validate` optionally accepts a candidate `schema`, which must pass as well as the reference contract. `benchmarkSuccess` is the fixed-reference diagnostic; `success/result` additionally enforce the runtime candidate gate.

| API | Purpose |
|---|---|
| `GET /health` | Health and execution-disabled status |
| `GET /providers` | Configured providers, never API keys |
| `GET /schemas/{domain}` | Built-in argument contract |
| `POST /extract` | LLM proposal only; never auto-confirmed |
| `POST /states` / `GET /states/{id}` | Create/read state |
| `POST /states/{id}/confirm` | Confirm the inspected version |
| `PUT /states/{id}` | Versioned edit; confirmation cleared |
| `POST /validate` | Validate a supplied envelope |
| `POST /generate` | Generate against confirmed state and validate |
| `POST /integrations/tavily/search` | Separately requested search API call |

Unknown domain/schema errors return 422; missing state returns 404; stale/unconfirmed state returns 409; missing/wrong configured backend token returns 401. No available model/key is a configuration error, not an invitation to silently choose a different model. Model refusals/clarifications are valid benchmark outcomes when expected, but they do not pass a runtime request expecting a concrete tool call.

## JSON Schema, OpenAPI, MCP, and ordinary APIs

- **JSON Schema** describes argument structure: required fields, types, enums, bounds, formats, and branches. Its registration/compilation happens before repeated evaluation. It does not establish intent, authorization, or API availability.
- **OpenAPI** describes this HTTP service's endpoints, request/response bodies, and authentication interface. FastAPI emits it at `/openapi.json`. An arbitrary OpenAPI file is **not** automatically treated as an argument schema: select/bundle the applicable request schema and explicitly convert unsupported dialects.
- **LLM APIs** transport messages to providers and return generations. The provider adapters implement their different wire protocols; API secrets stay in the backend.
- **MCP** could expose a tool that calls this validator, or invoke an executor only after its own checks. This repository does **not** implement an MCP server/client or claim that MCP automatically validates semantic intent. Its HTTP/Python interfaces are the integration boundary.

The experiment intentionally uses **schema-in-prompt generation**, not native tool calling or schema-constrained decoding. Those change the generation mechanism and should be tested as a separate experiment with consistent provider settings.

## Workflow 2: measure schema improvement or harm

The schema is an **input under test**. The expected answer is independently authored in the dataset. Generating both the candidate schema and expected answer using the same unchecked LLM would make the evaluation circular.

| Arm | What the model receives |
|---|---|
| A0 `no_schema` | Same task, tool name/description, argument names, common envelope instructions, context, and application policies; no argument JSON Schema |
| A1 `minimal_schema` | A0 + types, required fields, and field descriptions derived from the **reference**, or an explicit `--minimal-schema` |
| A2 `input_schema` | A0 + the exact candidate argument schema supplied with `--schema` |

All three arms use the **same fixed reference judge and semantic oracle**. A weak candidate cannot earn success by permitting bad arguments; an over-constrained candidate cannot redefine the reference task. Candidate-schema validity is reported separately. At runtime the supplied candidate must pass too.

Tasks/arms/repetitions are shuffled using a recorded seed. The same per-case generation seed is used across arms where supported. Run directory metadata fingerprints the dataset, schemas, provider/model, repetition count, repair policy, token limits, and decoding settings. Resolved model IDs are retained; changing routed models invalidates the comparison flag.

First-attempt performance is the primary endpoint. Final repaired success, repair rate, and transport retries are separate. Repair feedback can reveal ordinary validation failures or **publicly confirmed state** mismatches, but never hidden gold answers. A structurally valid wrong destination with no public authoritative state is not magically corrected using the benchmark oracle. Repair feedback can expose constraints even in the no-schema arm; therefore final-success results measure the **generation-plus-validator repair system**, not the isolated first-prompt schema effect.

### Dataset and schemas

| Domain | Tool | Cases |
|---|---|---:|
| flights | `search_flights` | 80 |
| hotels | `search_hotels` | 80 |
| calendar | `prepare_event` | 80 |
| payments | `prepare_transfer` | 80 |
| inventory | `reserve_stock_draft` | 80 |
| search | `search_web` | 80 |
| **Total** | | **480** |

Each domain includes 20 complete tasks and 10 each of reordered/paraphrased details, missing inputs, ambiguous inputs, confirmed-state conflicts, invalid inputs, and injection/refusal cases. The dataset contains argument calls, correct clarification, and correct refusal expectations. Payment amounts are integer minor units; no payment API is invoked.

These are **480 benchmark test cases, not 480 independently established public benchmark suites**. They are synthetic templates with limited linguistic diversity, no human-reviewed labels, and potential template correlation. `heschema dataset --build` deterministically rebuilds cases, all 36 schema fixtures, and provenance/hash manifest. `heschema dataset` audits oracles and counts. Add held-out human-authored tasks and external domain cases before making product-wide claims.

Schema fixtures intentionally explore richness vs correctness:

- `reference`: fixed scoring contract.
- `minimal`: types/required/meanings, fewer constraints.
- `rich`: reference + intent-preserving field descriptions.
- `weak`: unconstrained argument properties; probes expose under-constraint.
- `contradictory`: accepts nothing; probes expose false rejection.
- `complex-equivalent`: extra tautological branches preserving the reference acceptance set; tests complexity without redefining valid answers.

Run each candidate in a **different output directory**. Example:

```bash
heschema benchmark --provider groq --domain flights \
  --schema benchmarks/schemas/flights.complex-equivalent.json \
  --repeats 3 --repairs 2 --out results/groq-flights-complex
```

Without `--schema`, the supplied-schema arm uses the built-in reference for each domain. A supplied candidate must target a single domain. For Boolean/very weak candidates, the minimal arm still comes from the reference rather than from that candidate.

### Your own domain

Pass `--dataset PATH.jsonl --schema PATH.json`. Each JSONL case needs:

```json
{
  "id": "shipping-001", "cluster": "shipping-001", "domain": "shipping", "category": "complete",
  "prompt": "Prepare shipping for order A1 to Goa.",
  "context": {},
  "toolName": "prepare_shipping", "toolDescription": "Prepare shipping arguments, without executing.",
  "referenceSchema": {
    "type": "object", "required": ["orderId", "destination"], "additionalProperties": false,
    "properties": {"orderId": {"type": "string"}, "destination": {"type": "string"}}
  },
  "policy": {},
  "expected": {"action": "call_tool", "tool": "prepare_shipping",
    "arguments": {"orderId": "A1", "destination": "Goa"}, "missingFields": [], "reason": ""}
}
```

Keep one reference/tool/policy per domain. Use an unknown domain name to activate custom definitions; built-in names use their built-in contracts. If several paraphrases share an underlying intent, assign them the same `cluster` so the bootstrap resamples the intent as a unit. `expected` is used only by evaluation, never sent as provider context. Do not place gold labels in `prompt/context` accidentally. The HTTP state workflow currently supports the six built-in domains; custom domains are supported by the benchmark CLI.

## The maths: what the percentages mean

For task `i`, arm `a`, and repeat `r`, define:

```text
Y(i,a,r) = 1 if the first output has a valid envelope, passes the FIXED reference
           contract, matches expected action/tool/arguments or clarification/refusal,
           and passes declared policies; otherwise 0.
```

For an arm with N scheduled/completed observations, **first-pass success (FPS)** is `100 × ΣY/N`. Provider errors count as unsuccessful observations and are separately reported; complete error-free runs are required for the comparison-valid flag. The report's `fitnessPercent` is simply FPS for this model/task dataset—not an intrinsic universal schema-quality percentage.

Let `B` be baseline paired success as a fraction and `S` supplied-schema paired success:

| Metric | Formula | Example: B=0.60, S=0.80 |
|---|---|---:|
| Absolute uplift | `100 × (S − B)` | **+20 percentage points** |
| Relative improvement | `100 × (S − B) / B` | **+33.33%** |
| Error reduction | `100 × (S − B) / (1 − B)` | **50% fewer errors** |
| Harm | Negative uplift | e.g. −10 points means worse success |

These examples are **illustrative arithmetic, not measured model results**. Relative improvement is `null` when B=0; error reduction is `null` when B=1. No arbitrary zero/infinity replacement is used.

Effects are computed only on matching `(caseId, repeat)` pairs. Within each cluster, observations are averaged; clusters receive equal weight. With equal repetitions and one task per cluster this equals ordinary task success. The 95% interval uses **2,000 seeded bootstrap resamples of clusters**, retaining the paired arms and repeated trials together. Declared clusters are assumed exchangeable; undeclared template dependence can still make intervals too optimistic. One/few-cluster intervals are not convincing population evidence.

- Interval entirely above zero: evidence of improvement on this benchmark setup.
- Entirely below zero: evidence of harm.
- Includes zero: inconclusive, not proof that the schema has no effect.
- Exact **McNemar** two-sided p-value uses discordant first-attempt pairs (`wins/losses`) only when there is one pair per cluster. With repeats/dependent pairs it is `null` rather than pretending they are independent.
- Wilson 95% intervals describe arm proportions under independence; the **clustered paired interval is primary** for schema uplift. Avoid treating multiple domain/schema comparisons as confirmed discoveries without multiplicity correction or a held-out confirmatory run.

### Additional measurements

| Metric | Meaning |
|---|---|
| Call schema validity | Candidate-valid first outputs / tasks whose oracle expects a call |
| Semantic precision among valid calls (SPV) | Semantically correct first calls / candidate-valid first calls |
| Invalid rejection (IRR) | Candidate-rejected reference-invalid mutations / invalid mutations |
| False rejection | Candidate-rejected reference-valid arguments / valid probes |
| Retry rate | Tasks with a model repair attempt / tasks |
| Retry efficiency (RE) | `100 − retry rate` |
| Recovery rate | Initially unsuccessful tasks eventually succeeding / initially unsuccessful tasks |
| Final success | Task success after allowed model repairs |
| Model gap | Larger-model FPS minus smaller-model FPS on matched configuration |
| Model stability (MS) | `100 − abs(model gap)`; descriptive agreement, not a guarantee |

Mutation probes delete required fields, corrupt types, violate numeric minima, and add unexpected properties. They test **structural contract discrimination**, not whether a wrong but valid city matches user intent. Their construction is deterministic and limited; add boundary/branch/security probes for your domain.

The original proposed custom index is preserved as optional:

```text
Custom fitness = 0.45 × FPS + 0.20 × SPV + 0.15 × IRR + 0.10 × RE + 0.10 × MS
```

All components are percentages. These weights are **user-defined, uncalibrated, and not an industry standard or probability of safety**. The score is `null` until every component—including a matched second-model experiment—is available. It is not substituted for measured uplift, and does not directly include dollar costs or latency.

For cross-model sensitivity, run identical datasets/schema/repeats/repair/seed/token/temperature settings, then:

```bash
heschema compare-models results/small/report.json results/large/report.json
```

Supply the smaller model first. Both reports must be complete, configuration-matched, and `comparisonValid`; mock, provider-error, or unconfirmed/changing model-ID experiments are rejected. The model-sensitive threshold is provisionally a gap ≥15 points.

### Classifications are diagnostic flags, not causes

| Observation | Report interpretation |
|---|---|
| Validity ≥95%, SPV ≥90%, FPS ≥90% | `LLM-friendly` for this evaluated setup |
| Validity ≥95%, SPV <85% | `high-validity-low-semantic-accuracy`; inspect descriptions, intent/state and constraints |
| Validity <85% | Low validity; inspect errors before calling it over-complex |
| False rejection >0 on probes | `over-constrained-on-probes` |
| Invalid rejection <80% | `under-constrained-on-probes` |
| FPS <85%, final ≥95%, retry rate ≥15% | `retry-dependent` |
| Small/large gap ≥15 points | `modelSensitive: true` in matched two-model comparison |

Thresholds are provisional and configurable by editing `metrics.py`, not universal quality standards. Low validity alone cannot prove complexity; poor semantic accuracy alone cannot prove contradiction. Correct complexity comparisons should use logically equivalent schemas, held-out tasks, and sufficient samples.

## Time, cost, and request budgets

With 480 tasks × 3 arms × 3 repeats, a full experiment has **4,320 first-attempt calls**. With up to 2 repairs per call, the upper bound is **12,960 model generation calls**, before provider-internal transport retries. Free quotas may require many resumptions. Start small and estimate your own cost before running everything.

Supply your current/effective rates explicitly:

```bash
heschema benchmark --provider mistral --domain flights --repeats 3 \
  --input-price 0.10 --output-price 0.30 --out results/priced-example
```

The rates above are **illustrative inputs, not quoted Mistral prices**. Estimated token cost is:

```text
Cost = (inputTokens × inputUSDPerMillion + outputTokens × outputUSDPerMillion) / 1,000,000
Cost per successful task = total known cost / number of final successes
```

Usage includes completed repair attempts. Unknown usage/rates or provider errors leave cost unknown (`null`), not falsely free. Anthropic cache tokens are included in input totals; use effective blended rates or calculate exact tier/cache charges separately. Failed billable responses, infrastructure, hosted storage, Tavily, discounts, and batch pricing are not fully accounted for: check actual billing. A free/local model may still incur infrastructure cost.

Reports contain task-wall-clock p50/p95 (including pacing, completed retries, and validation), first-evaluation mean validation time, token totals, provider errors, transport retries, and repair counts. Hosted performance depends on queues/network/tokens; local validation speed alone is not an end-to-end LLM speedup.

If validation accounts for fraction `f` of total time and becomes `k` times faster, with everything else fixed, Amdahl's law gives overall speedup `1 / ((1 − f) + f/k)`. Example: 5× validation with f=1% produces only about **1.008× overall speedup**. Fewer bad generations/retries may matter more, but must be demonstrated by real paired runs. This project does not invent booking-loss or human-review savings from synthetic metrics.

## Optional Blaze integration and performance measurement

Sourcemeta's Blaze compiles JSON Schema into instruction templates. This integration uses the official `@sourcemeta/jsonschema` CLI compiler and `@sourcemeta/blaze` JavaScript evaluator, with pinned versions in `native/package-lock.json`.

```bash
npm ci --prefix native
export JSONSCHEMA_CLI="$PWD/native/node_modules/.bin/jsonschema"
HESCHEMA_TEST_BLAZE=1 pytest -q tests/test_blaze.py
heschema speed --engine jsonschema --iterations 10000 --out results/python-speed.json
heschema speed --engine blaze --iterations 10000 --out results/blaze-speed.json
heschema benchmark --provider mock --engine blaze --limit 8 --repeats 1 \
  --out results/blaze-offline
```

Use Node 22+ for the pinned evaluator. The optional package metadata lists LGPL-3.0-or-later for `@sourcemeta/blaze` and AGPL-3.0 for `@sourcemeta/jsonschema`; inspect upstream license terms for your intended deployment/distribution.

The worker is persistent, templates are cached, and compilation is not repeated per evaluation. Local state bindings snapshot typed canonical values so Python's `True == 1` cannot silently equate them. Schema caches are bounded; external references must be bundled instead of causing remote fetches.

**Do not interpret these commands as a native Blaze speed contest.** `heschema speed` measures the public HESchema validation path, including schema hashing, Python reference/format checking, and, for Blaze, IPC. The JavaScript evaluator currently lacks full format assertion and has numeric precision limits; Python retains an independent check. This conservative path can be **slower** than Python alone. The upstream “up to/around 10×” performance statement is workload-specific validation performance, not a guarantee for compilation, this wrapper, semantic checking, or total LLM latency. Native-kernel testing, trusted compiled-schema handles, and optimized in-process semantic bytecode would be future engineering work, not an existing claim.

## Results and reproducibility

Each run directory contains:

```text
config.json  dataset/schema hashes and experimental configuration
runs.jsonl   append-only rows with first evaluations, generations, repairs and usage
report.json  metrics, paired effects, probes, subsets, classifications and limitations
report.md    human-readable summary
```

`examples/offline-report.*` is a committed **offline smoke run**, not evidence that GPT, Claude, or any schema improved. Real model experiments were not run with user API keys during implementation.

Raw generations/prompts/state values in logs can be sensitive. `results/`, `data/`, `.env`, and local caches are ignored by Git. Add retention/redaction/encryption policies before using real customer data. Never publish reports with secrets or personal data without review.

## Security and limits

- Default server binds localhost. Set `HESCHEMA_API_TOKEN` before `heschema serve --host 0.0.0.0`; send `Authorization: Bearer ...` on protected endpoints.
- This is a **single-operator service**, not a multi-tenant authentication system. An API token authenticates the backend operator; it does not cryptographically attest who confirmed a state. Add a trusted identity provider, role separation, TLS, and audit events for production. Do not expose an unauthenticated ASGI factory directly.
- Schema structural validity does not prove intent; confirmed state can still be wrong if the user approves a mistaken extraction.
- Declared policies currently cover numeric ceilings and ordered ISO date fields. They are not comprehensive fraud/compliance/safety logic.
- Arbitrary schemas can be computationally expensive. External references are rejected, but schema size/depth/regex budgets, sandboxing, tenant quotas, and request limits require additional hardening for untrusted deployments.
- Fixed contract + exact canonical argument comparison is intentionally strict; equivalent aliases/timezones need independently reviewed normalization rules, not ad-hoc model judging.
- Concurrent state changes are detected, but because no external action executes here, there is no atomic booking/payment transaction. Never assume `PASS` solves a future executor's race conditions.
- API adapters are protocol-tested using mocked HTTP; hosted model/account compatibility must be checked with your credentials. No automatic fallback model is used because it would confound experiments.
- Keep benchmark labels independent of candidate/model output. Version your dataset, hold out test cases, use model snapshots where possible, and record actual model IDs/pricing.

## Development

```bash
ruff check src tests
pytest -q
heschema dataset --build
heschema dataset
```

Tests cover all 480 oracles, wrong-city semantics, duplicate/nonfinite JSON, bounds/formats, immutable typed state, schema registration, auth/confirmation/versioning, common scoring fairness, paired maths, resume/budgets, oracle isolation, provider protocols, search separation, and optional native parity.

```text
src/heschema/     API, CLI, providers, schemas, state, evaluation, metrics and benchmark engine
config/          provider registry (no secrets)
benchmarks/      committed 480-case dataset, manifest, and 36 schemas
native/          optional Blaze worker and pinned npm dependencies
tests/           unit, API, protocol and optional native integration tests
examples/        explicitly labeled offline reports
.github/         CI workflow
```

## Official implementation references

- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)
- [Sourcemeta Blaze](https://github.com/sourcemeta/blaze) and [JavaScript port limitations](https://github.com/sourcemeta/blaze/blob/main/ports/javascript/README.md)
- [OpenAI Responses/text API](https://developers.openai.com/api/docs/guides/text)
- [Anthropic Messages API](https://platform.claude.com/docs/en/api/messages/create)
- [Groq OpenAI compatibility](https://console.groq.com/docs/openai) and [rate limits](https://console.groq.com/docs/rate-limits)
- [Mistral first API request](https://docs.mistral.ai/getting-started/quickstarts/developer/first-api-request)
- [Gemini OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai)
- [OpenRouter API](https://openrouter.ai/docs/api-reference/overview)
- [Hugging Face Inference Providers](https://huggingface.co/docs/inference-providers/guides/first-api-call)
- [Ollama chat API](https://docs.ollama.com/api/chat)
- [Tavily search API](https://docs.tavily.com/documentation/api-reference/endpoint/search)

**Bottom line:** a report can say “this schema raised first-pass success by X percentage points, with this uncertainty, for this model and domain.” It cannot honestly say “this schema makes every LLM X% better” or “this validator guarantees safe payments.”
