# Latency measurement boundaries

Timing protocol: `latency-v1`. This instruments future runs. It does not rerun
models, change retry policy or establish that HESchema speeds up generation.
Historical logs and frozen study packs remain unchanged.

## Why the old measurements were insufficient

Inspection of parent commit `7f20dd6504362833608276150bf96a357078db4e`
found several different, overlapping timing scopes:

- `Generation.latency_ms` starts after adapter-lock and initial pacing waits,
  but includes HTTP calls, transport backoff and adapter parsing. It is not
  isolated inference time.
- Coordinator `requestLedger[].elapsedMs` also includes subsequent local
  evaluation and repair-feedback preparation. It is not HTTP response time.
- `validationMs` covers the validator callback's internal timer. With optional
  application calculations, it does not cover all pre-calculation input checks.
- `calculation.pipelineMs` covers the whole calculation/validation pipeline,
  including validation of the assembled output. Adding it to validation time
  would count overlapping work twice.
- The Contracts UI did not record its browser request elapsed time.

These fields remain for compatibility. New comparisons should use the explicitly
scoped timing evidence below. `totalObservedModelMs` in controlled reports is a
deprecated sum of legacy adapter latencies, not measured model inference time.
Legacy report latency percentiles also retain their previous outcome filtering.

## Provider adapter: client-observed phases

`Generation.metadata.timing`, `Generation.diagnostic().timing` and sanitized
`ProviderError.diagnostic().timing` carry this breakdown:

| Field | What is measured |
| --- | --- |
| `totalMs` | Entire adapter invocation, including lock acquisition and all waits |
| `queueWaitMs` | Waiting for this Provider instance's asyncio lock |
| `pacingWaitMs` | Deliberate initial request-interval sleep |
| `retryWaitMs` | Deliberate transport retry/backoff sleeps, using actual elapsed time |
| `providerResponseMs` | Sum of awaited non-streaming HTTP POST durations, including full response body receipt |
| `adapterOtherMs` | Adapter total minus those disjoint phases: request/response processing and remaining overhead |
| `httpAttempts` | Per-attempt duration, HTTP status when available, and sanitized outcome |

The HTTP duration includes client connection-pool waits, serialization, network
transit, remote queueing and remote execution. It cannot separate those costs or
establish token-generation throughput or time to first token. Failed HTTP attempts
and request timeouts also consume time; their status/outcome remains visible.
Error timings never include credentials, response bodies or request payloads.
Timeout/cancelled durations are interrupted observations; report them separately
from completed responses rather than interpreting them as completed generation time.

Ollama's existing provider-reported `durationsMs` are separate observations,
not additive phases of client wall time. Backend claims about load/generation
time must not be substituted for this client measurement.

Transport retries remain disabled by `request_generation` in bounded repair paths.
There, a measured `retryWaitMs: 0` is expected. A semantic repair is a new provider
call and can still incur pacing/queue waits. Direct adapter callers that already
allow transport retries now observe their waits separately; retry rules are not
expanded by this change.

## Coordinator: validation, calculation and all attempts

`repair.timing` in generation responses and `timing` in benchmark/controlled-study
rows have scope `repair_coordinator`:

| Field | What is measured |
| --- | --- |
| `totalMs` | Coordinator entry through final decision, before serializing its returned object |
| `requestWallMs` | Time awaiting generation callbacks, including waits and task cleanup; excludes evaluation |
| `localEvaluationMs` | Entire evaluation callback wall time for every attempted/replayed response, including any fallback empty-output check |
| `applicationCalculationMs` | Sum of explicit opted-in arithmetic calls, including failed calculations |
| `localValidationMs` | Evaluation wall time excluding the explicit arithmetic calls |
| `coordinatorOtherMs` | Remaining coordinator work, including context checkpoints, feedback, copying and bookkeeping |
| Provider phase fields | Sums from newly invoked, instrumented adapters; null if any invoked adapter lacks a complete breakdown |

The two accounting identities are:

```text
totalMs = requestWallMs + localEvaluationMs + coordinatorOtherMs
localEvaluationMs = localValidationMs + applicationCalculationMs
```

Provider phases are nested inside `requestWallMs`; validation and arithmetic are
nested inside `localEvaluationMs`. Do not add both a parent and its children.
Small residual scheduling/measurement overhead remains in the enclosing scope.

`localValidationMs` includes parsing, schema/context preparation, source checks,
relationship checks and output assembly performed by the evaluator. It is wall
time, not CPU time or the isolated schema-engine timer. A benchmark evaluator can
also perform its scoring checks inside this callback. An arbitrary asynchronous
evaluation callback may include awaited work.

Application calculation evidence now includes `calculation.computeMs` for calls
to the declared deterministic arithmetic implementation. `pipelineMs` remains its
broader parent timer. Context/schema checks still precede calculations; every
assembled result still passes full validation. A blocked calculation has zero
compute time if arithmetic was never attempted.

Per-attempt ledger entries retain `elapsedMs` and add `requestWallMs`,
`evaluationWallMs`, local validation/arithmetic durations and `providerTiming`.
`requestInvoked` distinguishes invoking an adapter from replaying an old response;
it does not assert that an HTTP request was sent. For example, an adapter can reject
an unsupported mode before HTTP. Existing `requestMade` and request budgets retain
their meanings.

Unknown phases remain null. `providerCallsMeasured`, `providerCallsUnmeasured`
and `providerBreakdownComplete` expose coverage. An opaque CLI adapter, a custom
stub, or an interrupted invocation without a returned timing snapshot retains its
observed request wall time but does not acquire invented provider/backoff values.
Old saved provider latency is excluded when replaying a first response; its fresh
local revalidation still counts. An uninstrumented calculation breakdown remains
unknown rather than being treated as free.

## Server and browser elapsed time

`/contracts/generate` adds `timing` with scope `contract_generation_handler`.
It measures handler entry through response preparation, including contract/context
lookup, prompt/projection work, provider setup/close and the coordinator.
`outsideCoordinatorMs` is the remaining handler work. Authentication/body parsing
before handler entry, response serialization and network delivery are outside it.

The Contracts UI adds `clientTiming` to displayed/downloaded evidence. Its scope
`browser_request_to_parsed_response` runs from immediately before the request until
the response body is parsed, or the request errors. This is the user-observed
response-ready duration: it includes browser/request preparation, server work,
network and JSON decoding. It excludes earlier form checks and final screen paint.
It uses `performance.now()` and does not subtract timestamps from the server's
clock. Failed requests retain their client timing with no invented validation
decision. An API-only caller must measure its own outer request duration.

## Reports and interpretation

Benchmark and controlled decoding/repair rows preserve coordinator timings.
Their configurations record `timingVersion`; changed configurations cannot resume
into the same output directory. Use new output directories after upgrading.

Reports provide totals, means, p50 and p95 for each phase, with measured/missing
counts and separate outcome groups. They include failed outcomes, not only
successful requests, and never infer phases from historical `latencyMs` values.
Values are cumulative per task/repair run, not per HTTP attempt. Per-attempt
durations are in the ledger. Empty/missing phase cohorts return null, not zero.
Separately computed phase percentiles are not additive, even for disjoint phases.
The benchmark Markdown report includes the separated phase table.

For a prospective speed comparison, freeze the tasks, model/version, output
budget, generation settings, calculation policy and repair allowance. Counterbalance
order; hold concurrency and request pacing constant; distinguish warm/cold backend
states and account for quotas. Preserve failures and provider status codes. Compare
first calls and cumulative repaired tasks separately, using task-level pairing and
uncertainty estimates that account for repeated/shared-template tasks. Report
provider response, local work, waits and outer elapsed time together.

Deterministic fake-clock and mock-transport tests verify accounting boundaries,
retries, failures, cancellation, replay exclusion, missingness, API integration and
browser evidence. They are not empirical speed measurements or recovery results.

## Primary references

- [Python performance counters](https://docs.python.org/3/library/time.html#time.perf_counter)
  describe elapsed-time measurement, including time spent sleeping. Differences
  within one clock are used; absolute client/server timestamps are not compared.
- [HTTPX event hooks](https://www.python-httpx.org/advanced/event-hooks/)
  note that response hooks can run before body reading. This implementation wraps
  the awaited non-streaming POST rather than treating a response hook as completion.
