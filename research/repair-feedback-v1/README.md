# Repair feedback investigation

Investigated on 20 October 2026. No new model requests were made. The historical
results below come from the same privately retained, hash-verified resumed pilot
archive audited in [the APP CALC investigation](../app-calc-regressions-v1/README.md).
This change does not edit that archive, its frozen input pack or its outcomes.

## What the saved repairs actually show

All 64 recorded repair attempts across the 809 verified results were grouped by
the first evaluation's saved diagnostic codes. Repeated codes within one slot
count once; multiple different codes would form a separate combined group.

| Prompt mode | Initial diagnostic code | Repair attempts | Recovered |
| --- | --- | ---: | ---: |
| FULL | `json_parse` | 10 | 3 |
| FULL | `sum_items_equals` | 15 | 0 |
| FULL | `schema_const` | 3 | 0 |
| COMPACT | `json_parse` | 3 | 3 |
| COMPACT | `sum_items_equals` | 18 | 3 |
| COMPACT | `schema_const` | 3 | 0 |
| APP CALC | `json_parse` | 11 | 0 |
| APP CALC | `schema_const` | 1 | 1 |

Thus FULL recovered **3/28**, COMPACT **6/24**, and APP CALC **1/12**. The code names
above are historical observations, not new runtime categories. `schema_const`
is a projected-constraint failure; the other labels describe parsing and sum-rule
failures. Task repeats are correlated observations, not independent user tasks.

The frozen pilot toolkit had its own feedback path: at most three diagnostics,
at most 600 characters, and generic messages such as a failed constraint/rule or
a request for valid JSON. It withheld source values and computed totals. Its
whole serialized list could be cut mid-JSON. That implementation is distinct from
the repository coordinator, so the production issues below cannot be asserted as
the cause of these historical recovery rates.

## Production gaps verified in code

At parent commit `dccb8d14c6cb40784361515f99e721713422562a`:

1. Actionable feedback copied complete validation messages, actual values and
   expected values. When the first entry exceeded the feedback budget, the loop
   stopped and sent an empty list, even if later errors were small.
2. Source-bound whole-array errors identified the array rather than the first
   changed field. Their messages could repeat large collections.
3. Relationship mismatch diagnostics were eligible for repairs, but
   `RELATION_TYPE_INVALID` was excluded despite its `correct_output` disposition.
4. The preceding APP CALC fix already added parser positions and syntax hints.
   Those are retained; no new parser capability is claimed here.

## Changes

`actionable` feedback is now versioned `category-v1`, grouping failures as invalid
JSON, source agreement, relationships, output schema or empty output. Routing uses
runtime diagnostics only; the research classifier and hidden correctness oracle
do not supply feedback.

- Source diagnostics retain the full original error and add a small first-mismatch
  view using active approved bindings. It names both output and context pointers.
  Arrays preserve order; booleans remain distinct from numbers; missing and null
  are different. Bound limits/allowed sets remain constraints.
- Relationship feedback uses the actual rule kind, inputs and protected fields.
  A date must be strictly before another date, not equal to it. Application
  calculation feedback does not ask the model to generate the omitted target.
- Whole entries fit the character budget through progressively smaller summaries.
  An oversized entry cannot hide later errors or produce a sliced JSON list.
- The coordinator records the exact feedback sent for each repair. Configurations
  identify feedback versions; changed versions cannot resume an existing study.

Retry allowance, request/token/deadline limits, context freshness, refusal,
clarification and truncation gates remain enforced. Every candidate still passes
strict parsing, original structure, approved-source checks and full relationship
validation. Invalid JSON is not automatically patched or accepted. Source values
and deterministic results can be restated only from runtime-approved bindings or
declared checks, never a hidden expected answer. This restatement itself can cost
tokens; no token-saving percentage is claimed for the new repair messages.

## Verification and reproducibility

The committed tests include labelled constructed failures using existing public
Crossref, PyPI and WfCommons records. Those mutations are test controls, not new
real model responses. Other small controls exercise JSON syntax, bounds, missing
values, pointer escaping, tool envelopes, dates, budgets and oracle isolation.

```sh
python -m pytest -q tests/test_repair_feedback.py tests/test_repair_coordinator.py \
  tests/test_app_calc_regressions.py tests/test_controlled_experiments.py
```

To reproduce the historical grouping privately, use the existing audit tool:

```sh
python scripts/analyze_app_calc_regressions.py \
  --archive /path/to/HESchema_Resumed_Pilot_Evidence.zip \
  --out results/category-repair/full-audit.json
```

Read `evidence.historical_repairs_by_diagnostic` in that local result. The audit
still verifies archive hashes, saved score reproduction, submitted initial prompts
and response/request links before returning the summary. It does not rerun the
provider. Its output includes private raw evidence; keep it local and uncommitted.
Only aggregate historical counts are published here.

## What still needs testing

Compare generic, raw and `category-v1` feedback on identical saved first responses
from new, frozen real-source tasks, with identical context, model, generation mode,
temperature, output limit and one-repair allowance. Keep initial generation cost
separate from newly incurred repair cost. Count every eligible failure, report
missing responses/provider failures, and keep category-specific denominators.
Record new eligibility for relationship type errors separately from changes to
message wording; do not attribute both effects solely to feedback phrasing.

Measure recovery, final correctness, false acceptance/rejection, all tokens, cost
and full latency. Preserve unsuccessful responses. Report results by task and
model, and account for shared templates and repeats in uncertainty estimates.
Changes to feedback, source-value repetition or calculation policy are separate
factors and should not be changed together when attributing effects.

The implementation establishes bounded, informative feedback and preserved gates.
It does **not** show better live-model recovery or a need for new schema keywords.

## Primary technical references

- [Instructor validation and reasking](https://python.useinstructor.com/concepts/reask_validation/)
  describes passing validation failures and prior responses to a bounded reask,
  with context-based validation. It does not validate HESchema's recovery rates.
- [Pydantic error handling](https://docs.pydantic.dev/latest/errors/errors/)
  documents typed errors, field locations and custom messages. HESchema continues
  using its own JSON Schema diagnostics; no dependency migration is introduced.
