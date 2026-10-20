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

Positive/negative controls, valid alternatives, reference-scope regressions and
coverage limitations are described in [validator controls](validator-controls.md).
Zero observed wrong acceptance does not establish complete validator coverage.

Rules: `product_equals` and `sum_equals` use exact integers and integer minor units.
Integral real values are accepted only within the safe IEEE-754 integer range;
fractions, booleans and unsafe reals fail. Arbitrarily large integer tokens use
exact Python arithmetic. `date_before` requires strict `YYYY-MM-DD` and strict
ordering; `equals` uses JSON value equality (numeric aliases match and booleans remain distinct); `reference_member` needs an
explicitly approved/verified context array. Schema and source checks precede
relationships. Missing evidence leads to clarification, never an invented answer.

`POST /contracts/generate` accepts provider/model, prompt, mode, `promptStyle`, optional context,
`repairs` (default 0), `maxRequests`, `maxTokens`, `tokenBudget`, `deadlineSeconds`,
and `feedbackStyle` (`generic`, `raw`, `actionable`). Output-token budgets reserve
the advertised cap per request; they are not a bound on input tokens or a billing
estimate. Repairs do not execute tools, infer approvals, or use benchmark gold.
Refusal/clarification, stale context, truncation, provider rejection and exhausted
budgets stop the coordinator. Provider transports are single-request in this path;
transport retry accounting remains distinct. Every started request, including
cancelled/failed ones, is recorded. Unknown usage remains unknown. Repair of a
schema-valid but silently wrong unbound field cannot use a hidden oracle.

Generation and study evidence also includes versioned, separated timing for HTTP
responses, adapter waits, local validation/calculation and coordinator elapsed time.
The Contracts UI records browser response-ready time separately. See
[latency measurement boundaries](latency-measurements.md) for scopes, missingness,
reporting and the limits on speed claims.

### Category-specific repair feedback

The default `feedbackStyle: "actionable"` now uses `category-v1`:

- `invalid_json`: keep parser reason, offset and line/column when available;
  request a complete JSON value while preserving approved fields. Duplicate keys
  and non-finite values do not acquire invented decoder positions.
- `source_value`: identify the first differing bound field and its approved
  context pointer. Small values can be included; entire author/file arrays are
  not repeated. Missing values are distinct from explicit nulls. `enum`,
  `minimum` and `maximum` are labelled constraints, not replacement values.
- `relationship`: identify the rule, kind and input locations. Arithmetic,
  date ordering, membership and uniqueness get different instructions; protected
  approved inputs must remain unchanged. Type/format violations are eligible
  for the same bounded repair budget. Application calculation feedback asks for
  corrected inputs while leaving computed targets omitted.
- `schema`: identify the output field, schema location and failing keyword;
  keep concise branch diagnostics for compound constraints.

Source and relationship locations are relative to the contract document, or to
`arguments` for a tool envelope. Legacy confirmed-state feedback explicitly uses
an `/arguments/...` pointer. The original diagnostics remain available in each
evaluation. The feedback is a bounded summary, not an exhaustive list of errors
or permission to bypass any checks. Large values are marked as omitted; very
small character budgets retain only category/code/location when space permits.
Whole JSON entries are packed instead of slicing the serialized feedback. A large
first error no longer silently prevents useful feedback for subsequent errors.

`generic` and `raw` retain their existing rendering strategies. The coordinator
returns `feedbackVersion`; attempts requesting a repair record the actual message,
character count, style and version in `repairFeedback`. Benchmark and repair-study
configurations also record versions, preventing a resume from silently combining
feedback implementations. Use a new output directory after upgrading; historical
pilot records and their messages must stay unchanged.

These are deterministic diagnostic improvements. They do not establish an increase
in model recovery, lower token usage or lower latency. The historical breakdown,
public-source controls and prospective comparison plan are in
[the repair feedback investigation](../research/repair-feedback-v1/README.md).

## Full and compact contract prompts

`promptStyle` is independent of the decoding `mode`:

- `full` (the default) preserves the existing prompt: effective schema with approved
  constraints, relationships, binding evidence including values, and trusted facts.
- `compact` sends the original output schema, declared relationships, active binding
  instructions without values, missing required binding locations, and trusted facts.
  Approved values are not copied into additional `const`/`enum`/bound constraints or
  repeated inside binding evidence. Original constraints already authored in the
  contract remain intact. Facts still come only from approved pointers or verified
  fact records; this setting does not approve additional context.

For example, after registering a contract and confirming its context:

```json
{
  "contractId": "invoice-demo",
  "contractVersion": "1",
  "contextId": "<confirmed context id>",
  "contextVersion": 1,
  "prompt": "Prepare the invoice from the approved facts.",
  "provider": "ollama",
  "mode": "prompt_only",
  "promptStyle": "compact",
  "repairs": 0
}
```

Select **Prompt style** in the Contracts & Context generation controls, or supply
the API field above. Responses and downloaded evidence identify `promptStyle`.
Omitting it selects `full`; unknown styles return HTTP 422 before inference.

Both styles construct and validate the full effective schema locally, check original
structure, source bindings and relationships, and use the same context freshness
checks and repair budgets. Removing context projections from the generation prompt
does not remove them from validation. A compact answer that passes the original
schema but disagrees with an approved fact is still rejected. Refusal and clarification
remain available for tool envelopes. No path authorizes execution.

With native decoding, `native_original` sends the selected style's envelope as the
provider schema: effective for `full`, original for `compact`. `native_projected`
applies the existing conservative provider transformations to that selected envelope.
Its projection manifest describes that generation schema, not an equivalence between
the original and context-constrained schemas. Compact native schemas do not enforce
the omitted context bindings; the unchanged local contract gate enforces them.
`/contracts/effective-schema` and `/contracts/validate` are unaffected.

The motivating pilot observed 20.65% fewer total tokens for COMPACT on its matched
tasks. That is a historical observation, not a promised saving for this runtime:
small contexts, original schemas, task text and repair frequency affect usage.
This implementation adds no new model benchmark or latency/accuracy claim. Full
remains the default pending confirmation on untouched tasks. This option applies
only to `/contracts/generate`, not legacy generation or frozen research runners.

## Optional application calculations

Arithmetic relationships remain checks by default. Opt in **per relationship** by
adding `"compute": "application"` in a new contract version. Omitting `compute` or
setting it to `"model"` preserves model generation and existing validation. There
is no global enable switch and the server never selects relationships automatically.

Supported kinds use the same exact-integer implementation as their relationship checks:

| Kind | Application result |
| --- | --- |
| `count_equals` | Length of the array at `arrayLocation` |
| `sum_items_equals` | Sum of each array element's integer at `itemLocation` |
| `sum_equals` | Sum of values at `operands` |
| `product_equals` | Product of values at `operands` |

For example, this relationship tells the application to calculate the count:

```json
{
  "id": "item-count",
  "kind": "count_equals",
  "arrayLocation": "/items",
  "target": "/itemCount",
  "compute": "application"
}
```

See [the complete count-and-sum example](../examples/contracts/application-calculations.json).
Register its contract, create and confirm its context, then call
`/contracts/generate` normally. The example is synthetic documentation, not study
evidence. Both prompt styles and all existing decoding modes support the option.
For opted-in contracts, projection manifests describe the reduced generation
schemas, not the full assembled-output schema.

The model returns the input fields and any fields still assigned to the model;
it must omit only the application-computed targets. The generation schema removes
those properties and their required entries, preserving the remaining constraints
and approved source projections. Tool envelopes retain call/refusal/clarification
branches. A response that includes a computed target is rejected, not silently
overwritten. There is no automatic fallback to a different computation policy.

The runtime performs these steps for each initial or repair response:

1. Parse the entire output strictly and require valid input structure and completion.
2. Check all approved bindings and required context before calculating anything.
3. Calculate every selected value, then assemble them atomically into a copy.
4. Validate the assembled output against the **full original and effective schemas
   and every declared relationship**, including rules not assigned to the application.

Incorrect source values, invalid JSON, booleans, fractions, unsafe real-valued
integers and missing operands cannot be repaired by inventing or rounding values.
Empty arrays have count and sum zero; large integer tokens use Python's exact
arithmetic. Calculated values must still satisfy their original target constraints.
Unbound inputs receive structural checks, not independent source verification;
calculating a consistent total does not prove those inputs are true.

To avoid unsafe general schema rewriting, this initial implementation requires a
plain, closed root object (`type: object`, `properties`, `additionalProperties: false`)
with top-level integer target properties. Root composition/conditionals, references,
root property-count constraints and other unhandled root keywords are rejected.
Input properties may contain nested structures and constraints without references.
Targets must be distinct, must not overlap context bindings, and must not be inputs
to any application calculation. Chained, self-referential, nested-target or arbitrary
expression calculations are rejected at registration. There is no `eval`, source-code
execution, or new JSON Schema keyword involved.

For opted-in generation, `modelOutput` is the untouched last model response and
`output` is the assembled whole JSON when calculation was applied (otherwise the
raw response). Each repair attempt also preserves its original `generation.text`,
reported tokens and timing. `validation.calculation` records status, selected rule
IDs, input/source check results, calculated values, and
`correctnessScope: "assembled_system_output"`. A valid assembled answer is a system
result; it is not evidence that the model performed the arithmetic correctly.
`calculation.pipelineMs` includes input/source validation, assembly and final validation;
provider transport is excluded and remains in the generation/run timing records.
Refusal, clarification and known truncation skip calculation. Context changes stop
the run, and no output authorizes execution.

`/contracts/validate` remains read-only validation of a complete output: it never
fills missing fields or corrects arithmetic. Existing contracts, validation results,
research inputs and benchmark runners are not automatically migrated. Given the
pilot's model/source regressions, opt in selectively and confirm the chosen design
on untouched tasks before making accuracy, latency or token-saving claims.

The [saved-response regression investigation](../research/app-calc-regressions-v1/README.md)
reproduces the pilot's Crossref/GPT OSS 20b failures. Those final failures were JSON
syntax errors before calculation, not demonstrated arithmetic or mapping failures.
Runtime `JSON_INVALID` errors expose parser locations and syntax guidance when
available; actionable repair feedback carries those details without altering raw
output or weakening source checks.

## Native decoding and diagnostics

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
