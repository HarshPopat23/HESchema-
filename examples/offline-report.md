# HESchema benchmark report

Provider: **mock**; model: `offline-stub`.
Cases: 480; completed runs: 4320; complete: True.

## First-pass valid and correct task success

| Arm | Success % | Final success % | Retry % | Errors | p95 ms |
|---|---:|---:|---:|---:|---:|
| no_schema | 12.5 | 12.5 | 0.0 | 0 | 0.0861835499335939 |
| minimal_schema | 12.5 | 12.5 | 0.0 | 0 | 0.08818405030979191 |
| input_schema | 12.5 | 12.5 | 0.0 | 0 | 0.09086900004149355 |

## Paired schema effect

- versusNoSchema: 0.0 percentage points; relative 0.0%; 95% clustered bootstrap interval [0.0, 0.0].
- versusMinimalSchema: 0.0 percentage points; relative 0.0%; 95% clustered bootstrap interval [0.0, 0.0].

## Interpretation limits

- Synthetic template benchmark: human review and external test sets are required before broad claims.
- Wilson intervals assume independent runs; clustered paired bootstrap is the main uplift interval.
- Prompt-only schema effect; constrained decoding requires a separate experiment.
- Cost excludes infrastructure/search and uses user-supplied effective token rates.
- MOCK ONLY: fixed stub output; no empirical LLM/schema improvement claim.
