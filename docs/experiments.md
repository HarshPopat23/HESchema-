# Controlled measurements

The existing `benchmark` command studies schema richness in prompts. Its CLI repair
default remains two (UI jobs default to zero). It now uses the shared coordinator
and fingerprints protocol/feedback/code/dependency settings. Use a new output
folder for protocol 2. Historical reports and C01–C10 fixtures are not rewritten.
`heschema report old/report.json` prints a labeled, read-only legacy adapter.

Stage A uses `decoding-study`, with zero repairs and identical message hashes for
`prompt_only`, `native_original`, and `native_projected`. Projection is a separate
factor; it is not pooled into the original native-vs-prompt comparison. Held-out
H01–H08 are new author-created synthetic cases covering source errors, arithmetic,
conditionals, uniqueness, overlapping unions, bounds, local refs and missing context.
A tool's free-form reason is not compared to a gold reason. Exact requested document
outputs are scoring oracles only; they never become runtime context or feedback.

```sh
heschema decoding-study                         # 24-request dry run, no inference
heschema decoding-study --execute --provider mock --max-requests 24 --out results/mock-decoding
heschema repair-study --first-out results/mock-decoding
heschema repair-study --execute --provider mock --first-out results/mock-decoding --max-requests 216 --out results/mock-repair
```

Stage B replays each saved first output across feedback styles and budgets. First
output hashes are identical; replay costs are excluded from new model usage and
request counts. Re-validation is included. Records with no generated output are
reported as unavailable for repair. Provider/model, case/prompt hashes, sampling,
engine and source fingerprints must match. Synthetic mutations require explicit
`synthetic_mutation` provenance; no included mutation is labeled a natural failure.

Real runs require an available backend, `--execute`, and an explicit request budget.
Prepare the dry run first. Warmup is opt-in and logged outside task metrics. Mode
order is shuffled reproducibly; seeds/caps/temperature and requested thinking state
are recorded. Ollama backend version and requested model digest are read when
available, and generated resolved identities must be confirmed. Unknown metadata
stays unknown. Code hash, commit, dependency versions and available CPU metadata
are recorded; infrastructure and unobservable components are not inferred.
No live inference was run as part of this implementation.

Reports keep attempted requests, accepted requests, completion outcomes, whole JSON,
original schema, approved context, relationships, intent agreement, first/final
success and recovery separate. Both attempted and evaluated denominators are shown.
Failed/rejected durations remain visible by outcome. Known truncation or empty final
content cannot produce success. The paired bootstrap clusters by case/family;
paraphrases and repeats are not treated as independent samples. Capability profiles
record observed validity/violations/rejections separately from documented support;
a passing example cannot establish universal enforcement.

`designValid` checks provenance/completeness/identity. `comparisonValid` additionally
requires empirical, fixed-model evidence. Expected native request rejections are
measured outcomes and do not trigger an outage breaker. The cause of a rejection
and model identity of a rejected request remain unknown. Unexpected failures and
missing records limit interpretation. There are no general latency, throughput,
recovery-rate or adoption claims from the mock smoke checks. Input-token usage and
failure costs stay unknown when an adapter does not expose them.

The historical `scripts/run_cli_suite.py` defaults to a dry run and requires an
explicit execution budget (four invocations per pair); use the controlled study for
causal decoding comparisons. Do not overwrite old pilot evidence with protocol 2.
