# Contracts, approval and repair

The six existing domain endpoints remain compatible. The `/contracts` registry
also accepts third-party definitions through the API or `ContractRegistry.register`.
Server registrations persist in the same SQLite database as contexts. A contract
ID/version is immutable; changed definitions require a new version. Library callers
can use an in-memory registry or supply a SQLite path. No edit to `DOMAINS` is needed.

A definition includes `id`, `version`, `schema`, `outputKind` (`document` or
`tool_envelope`), optional `tool`, `contextSchema`, `bindings`, and `relationships`.
Bindings map an instance JSON Pointer to a context JSON Pointer using `const`,
`enum`, `minimum`, or `maximum`. Required bindings default to true. Only explicitly
approved pointers or declared verified facts can supply these values. Partial
approval binds the declared approved fields; it does not approve other fields.
The effective schema retains the original root and conjoins constraints, including
local references. Projection requires explicit object/array types on nested paths;
array indices are bounded to 1024. Obvious field-level conflicts are rejected
before inference; this is not a general schema satisfiability solver.

Create `/contexts`, inspect the proposal, then confirm its specific version via
`/contexts/{id}/confirm`. Extraction through the old endpoint remains unconfirmed.
An external fact declares a pointer, source, version, `verified: true`, and a
zone-aware expiry. These are operator attestations: HESchema does not independently
verify the source. The store enforces ownership; approval and facts have optional
and mandatory expiries respectively. Invalidate approval and create a new context
to refresh facts. A context change stops generation/repair rather than authorizing
new values. API authentication still models one operator, not a multi-tenant identity
system. Library callers must supply trusted snapshots and enforce their own ownership.

`POST /contracts/validate` checks existing output without inference. String output
means raw whole JSON; object/array/number/boolean/null values are accepted directly.
Omitting output means no generated document. Diagnostics use the empty pointer at
root and escape slash/tilde. Original schema, effective constraints, approved input
agreement, and relationships are separate stages. `PASS` covers only declared
approved bindings and rules; `intentScope` identifies that limit. Schema-only
validity is `NOT_CHECKED`, missing approval is `NEEDS_CONTEXT`, and refusal is
`REFUSED`. `accepted` means the declared validation/control checks allow the output;
it is not an execution permit. Decisions include an evaluation timestamp and context version; consumers must recheck freshness at their own boundary. All paths retain `executionAuthorized: false`.

Rules: `product_equals` and `sum_equals` use exact integers and integer minor units.
Integral real values are accepted only within the safe IEEE-754 integer range;
fractions, booleans and unsafe reals fail. Arbitrarily large integer tokens use
exact Python arithmetic. `date_before` requires strict `YYYY-MM-DD` and strict
ordering; `equals` uses JSON value equality (numeric aliases match and booleans remain distinct); `reference_member` needs an
explicitly approved/verified context array. Schema and source checks precede
relationships. Missing evidence leads to clarification, never an invented answer.

`POST /contracts/generate` accepts provider/model, prompt, mode, optional context,
`repairs` (default 0), `maxRequests`, `maxTokens`, `tokenBudget`, `deadlineSeconds`,
and `feedbackStyle` (`generic`, `raw`, `actionable`). Output-token budgets reserve
the advertised cap per request; they are not a bound on input tokens or a billing
estimate. Repairs do not execute tools, infer approvals, or use benchmark gold.
Refusal/clarification, stale context, truncation, provider rejection and exhausted
budgets stop the coordinator. Provider transports are single-request in this path;
transport retry accounting remains distinct. Every started request, including
cancelled/failed ones, is recorded. Unknown usage remains unknown. Repair of a
schema-valid but silently wrong unbound field cannot use a hidden oracle.

Native mode currently supports Ollama (and the nonempirical mock adapter), without
silent fallback. The full tool envelope includes clarification and refusal.
`native_original` and `native_projected` retain original validation. Transformations
are restricted to finite required string-tag conditionals, compatible shared tagged
objects, escaped literal slashes, and acyclic local `$defs` references. They preserve
validation outcomes for their declared subset; annotation collections are not
promised equivalent. URI scopes, dynamic references, unevaluated checks, arbitrary
overlapping unions and Unicode `\d` normalization are deliberately not rewritten.
`uniqueItems` stays intact. Manifests record hashes, preconditions, location mappings,
residuals and rejected transformations. Residual enforcement is unknown, not proven
unsupported. JSON canonical serialization is an identity mechanism only.

The compatibility endpoint preserves raw content and returns independent diagnostics
in `heschema.validation`; `strict` requests native enforcement, not a validity promise.
Reasoning never substitutes for final content. Finish reasons may be null. CLI stdout
is a report; only its explicit `document`/`raw` field is model output, including on a
nonzero exit. Optional CLI repair uses separately logged invocations, not a nonexistent
upstream retry flag. CLI invocation counts are labeled; upstream request counts are
unknown. Child processes are terminated and awaited on timeout.

Python supplies Draft 2020-12 and format diagnostics. Optional Blaze provides a
Boolean native cross-check; application rules are not Blaze vocabulary support.
Timing fields separate registration, native IPC, Python reference checks and total
validation. Ollama model/load/prompt duration components are retained when available;
queue time, GPU details and absent fields remain unknown.

The job registry remains process-local. This MVP does not add durable multi-worker
jobs, production execution, distributed approvals, or new custom vocabularies.
