# Researching recurring structured-output failures

The immediate goal is to identify reproducible categories before proposing a
custom JSON Schema vocabulary. This change adds application checks, labelled
prospective cases and observation reports. It does not introduce custom schema
keywords or claim that the categories are common in production.

## Distinguish the problem from the proposed solution

* **Standard authoring constraint:** `dependentRequired`, `if`/`then`, `const`,
  `enum`, bounds, `not`, and whole-item uniqueness are existing keywords. Test
  those as controls; do not call a missing keyword a vocabulary gap when an
  ordinary schema can express the requirement.
* **Dynamic property relationship:** a chosen value belongs to another array,
  two fields agree, a date precedes another date, a count equals array length,
  or a total equals the sum/product of source values. The general checks in
  this implementation are deterministic application rules. Bounded cases may
  be expressible by enumeration; this is not a proof of schema inexpressibility.
* **Trusted-context requirement:** a relationship can hold over wrong operands.
  Bind approved source fields separately before evaluating relationships.
* **Source interpretation:** an answer can satisfy all declared checks and
  still contradict the source or task. Keep the held-out expected answer out of
  generation messages, runtime checks and repair feedback.
* **Provider coverage:** schema request rejection, invalid returned instances
  and unsupported adapters are different observations. A violation alone does
  not establish an unsupported keyword, nor does a valid sample prove support.

## Available relationship checks

All paths use RFC 6901 JSON Pointers, including escaped tokens and the empty
root pointer. Register a contract to validate options before evaluation.

| Kind | Options after `id`, `kind` | Meaning |
| --- | --- | --- |
| `equals` | `left`, `right` | Semantic JSON equality; numeric aliases match, booleans remain distinct |
| `date_before` | `left`, `right` | Strict `YYYY-MM-DD`, left strictly earlier than right |
| `product_equals`, `sum_equals` | `operands`, `target` | Exact integer arithmetic |
| `reference_member` | `target`, `contextLocation` | Value belongs to an approved context array |
| `member_of` | `target`, `arrayLocation` | Value belongs to an array in the output document |
| `count_equals` | `target`, `arrayLocation` | Target equals the array length |
| `sum_items_equals` | `target`, `arrayLocation`, `itemLocation` | Target equals the sum of the selected integer field in each array element |
| `unique_by` | `arrayLocation`, `itemLocation` | Selected per-record values are distinct |

Empty arrays have count and sum zero and satisfy uniqueness. `member_of` fails
on an empty array. Arithmetic rejects booleans, fractional values and unsafe
real-valued integer operands; arbitrary-size Python integers remain exact.
Missing evidence fails closed. Relationship diagnostics identify the kind,
input locations and protected approved fields. Actionable feedback includes
these pointers, but validation still checks the complete response after repair;
feedback is not a guarantee that a model will preserve the fields.

The four arithmetic kinds also accept optional `compute: "model" | "application"`.
The default remains `model`. Application calculation is an explicit per-rule contract
choice, restricted to supported schemas; it validates inputs before assembly and
runs all original checks afterward. Other relationship kinds do not accept this
option. See [calculation semantics and restrictions](contracts-and-repair.md#optional-application-calculations).

## Provider controls and whole final content

`OLLAMA_THINK=false` is the default. `true`, `default`, `low`, `medium` and `high`
are explicit alternatives; supported values depend on the model. `default`
omits the field. Controls are frozen when a provider instance is constructed,
recorded in the study config, and reused for repair. The adapter reads available
backend version, model digest and `/api/show` thinking metadata. Missing metadata
stays unknown; there is no claim the backend honored a setting merely because
the client requested it.

Each returned generation fingerprints the actual submitted JSON body and records
message/schema hashes, seed actually sent, output cap, temperature and reasoning
settings. Headers and API keys are excluded. This is request evidence, not a raw
network capture or an independent backend attestation. Raw generation text and
separate reasoning fields are retained. HESchema does not strip thinking tags or
extract a JSON-looking substring.

If thinking was explicitly disabled but separate reasoning or non-JSON thinking
markers appear in a measured response or warmup, `controlChecks` identifies the
records and `comparisonValid`/`designValid` are false. These checks cannot detect
every possible prose reasoning trace. Inspect a pilot manually before scaling.
Tags inside otherwise valid JSON strings remain ordinary data.

Groq now implements the native `json_schema` request with `strict: true`, retaining
separate reasoning and response identity metadata. GPT-OSS requests use low
reasoning effort in every arm and no unsupported seed. Native rejection never
falls back to prompt-only or a weakened schema. Other unimplemented adapters
continue to report unsupported mode.

## Failure reports

`firstFailureCategories` and `finalFailureCategories` are separate. Categories
overlap, are versioned, and use attempted-row denominators. They include JSON
syntax, numeric range, reasoning in content, thinking-control mismatch, empty or
truncated content, original-schema violations, trusted-context mismatches,
missing evidence, relationship kinds, runtime-accepted oracle mismatch, adapter
unsupported mode and provider rejection/failure. Schema keywords are observations,
not inferred support declarations. Wrong-task answers are not automatically
classified as an arithmetic or source bug without the corresponding evidence.

`firstRelationshipChecks`/`finalRelationshipChecks` show valid, invalid and
missing-evidence rule outcomes. `schemaValidRelationshipRejected` counts the
specific cases the additional relationship layer catches. `finalStages` avoids
substituting overall task success for final JSON/schema validity. `byFamily`
keeps families separate, `byCategory` uses the intended case labels, and repair
`bySourceMode` avoids treating mixed decoding
modes as one recovery population. Pooled legacy arm summaries remain available
but are explicitly labelled in the report warnings.

The parser still uses finite binary floats. Extreme nonzero values that underflow
to zero are now rejected rather than silently becoming zero. The legacy
`JSON_INVALID` diagnostic is classified as `numeric_range`; a number can be valid
JSON syntax yet outside this implementation's supported range. Scoring uses
semantic JSON equality (`1` equals `1.0`, but not `true`) and records its version.
No historical result file is rewritten. Use a fresh folder after code changes.

## Experiment sequence

1. Run `heschema research-audit` and independently review the prospective pack.
2. Select a pilot balanced across categories, including successes, negative
   controls, empty arrays, boundaries, wrong-source operands and standard-keyword
   controls. Run multiple models with matched caps and recorded thinking settings.
   Keep model/backend/hardware results separate.
3. Inspect actual final content, control checks and eligibility before the main
   three-repeat campaign. All decoding-study arms currently receive the same
   schema-grounded prompt. This is **not** a schema-versus-no-schema experiment.
4. Replay each saved first output across generic/raw/actionable feedback and
   budgets 0/1/2. Record natural failures separately from synthetic mutations.
   Show failed request costs, missing outputs, recovery denominators and changes
   to previously correct fields. A runtime-accepted oracle-wrong answer must not
   receive hidden-answer feedback.
5. Make a descriptive category table from compatible saved first-pass reports:

   ```sh
   heschema category-report results/model-a/report.json results/model-b/report.json \
     --out results/category-comparison.json
   ```

   Dataset, cap, temperature, engine, taxonomy/scoring versions and evaluator
   code/dependency fingerprints must match. Repeat counts can differ and remain
   visible in the denominators. Models are not pooled; mock and invalid-control
   reports retain their evidence flags and do not become empirical results.
6. Replicate promising categories on permissioned real application cases. Show
   cases where the check adds value, cases ordinary schema authoring already
   solves, cases no rule catches, and cases projection/repair makes worse.

Only then consider a vocabulary proposal with an explicit semantics, boundary
cases and evidence that the requirement recurs. Synthetic task variants are not
independent users; do not advertise a semantic 80/20 distribution from this pack.

## Real-schema and task collection

Start with the pinned sources in the pack and [the use-case intake](use-case-intake.md).
Collect the original schema plus intended task, relevant source/state version,
desired relationship, expected output, naturally observed whole output (when
available), model/backend/version, workaround, review status and publication
permission. A repository schema proves an implementation exists; it does not
prove a real user encountered an LLM failure. Clearly label adaptations and
inferred constraints. Do not scrape private schemas or publish withheld records.

The source manifest includes exact commit URLs, excerpt hashes, relevant line
ranges and upstream licensing text. It documents filesystem head/tail exclusion
and memory relation endpoint existence. The tasks and graph snapshots remain
authored. Voluntary developer submissions need independent review and explicit
permission before inclusion in a published dataset. No outreach is sent by this
implementation.

## Primary references

* [JSON Schema conditional validation](https://json-schema.org/understanding-json-schema/reference/conditionals): property dependencies and conditional subschemas already exist.
* [Draft 2020-12 validation](https://json-schema.org/draft/2020-12/json-schema-validation): standard keywords and numeric interoperability.
* [Ollama thinking](https://docs.ollama.com/capabilities/thinking) and [structured outputs](https://docs.ollama.com/capabilities/structured-outputs): requested settings, separate fields and native format input.
* [Groq structured outputs](https://console.groq.com/docs/structured-outputs): strict JSON Schema request shape; observe eligibility separately.
* [Pinned public MCP evidence](../research/relationship-categories-v1/sources.json): exact source revisions, excerpts and license.
