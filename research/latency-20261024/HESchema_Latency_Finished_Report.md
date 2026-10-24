# HESchema latency replication — 24 October 2026

Completed: **2,160/2,160 slots; 0 remain**. The planned design covers 60 reused public-record adaptations from ten projects, three models, three repeats and four approaches.

**This is a segmented parallel-batch measurement, not proof that HESchema universally makes models faster.** The execution host reset after 635 completed slots. A second session was stopped by a network-policy rejection after another 680 complete slots. A third session completed the remaining 845 identities, reusing three intact initial responses. Timers for those reused responses cover resumed processing only; their whole matched groups are excluded from primary latency. Original completed responses were not regenerated.

All 2,160 result identities are now covered and verified across three sessions. Historical incomplete physical receipts remain explicitly unknown; completing a replacement does not reconstruct their missing timings.

Primary analysis: **532 matched groups (2,128 results; 532 per arm)**. Excluded observed groups include 8 touched by either earlier interruption, 6 crossing execution sessions and 0 without all four completed arms (categories may overlap). Exclusions affect the primary comparison only; all completed correctness/token outcomes remain in the JSON appendix.

## Primary results

A = ordinary schema; B = FULL contract; C = COMPACT contract; D = COMPACT plus declared arithmetic calculations. D otherwise matches C. All allow one detector-triggered repair.

| Approach | Final correct | Wrong accepted | Mean total tokens | Service median / p95, s | HTTP total median / p95, s |
|---|---:|---:|---:|---:|---:|
| A | 485/532 (91.17%) | 42 | 636.1 | 14.979 / 22.495 | 5.283 / 9.470 |
| B | 481/532 (90.41%) | 0 | 1146.0 | 15.157 / 31.215 | 5.907 / 13.460 |
| C | 475/532 (89.29%) | 0 | 946.4 | 15.189 / 31.236 | 6.064 / 13.144 |
| D | 479/532 (90.04%) | 0 | 988.5 | 15.243 / 30.920 | 6.017 / 13.942 |

**Observed finding:** COMPACT used 17.42% fewer total tokens than FULL in the matched sample. COMPACT's HTTP median was 6.064s versus FULL's 5.907s. This does not show a speed improvement. Contract arms accepted zero observed wrong final answers; the ordinary-schema arm accepted 42. This is an observed validation benefit on this sample, not guaranteed correctness or evidence that conventional application checks could not catch the same errors.

## Timing components

| Component: median / p95, ms | A | B | C | D |
|---|---:|---:|---:|---:|
| serviceTotalMs | 14979.08 / 22494.75 | 15157.43 / 31215.23 | 15189.04 / 31236.33 | 15242.73 / 30920.08 |
| providerRoundTripMs | 5283.38 / 9470.19 | 5907.49 / 13459.98 | 6064.13 / 13143.87 | 6016.89 / 13942.29 |
| activePipelineMs | 5304.92 / 9477.88 | 5920.17 / 13477.73 | 6078.90 / 13157.81 | 6035.31 / 13979.29 |
| localValidationMs | 0.20 / 0.60 | 3.04 / 9.23 | 2.96 / 9.74 | 3.95 / 15.93 |
| applicationCalculationMs | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.02 |
| pacingWaitMs | 9601.82 / 13794.32 | 10073.10 / 20255.13 | 10298.84 / 20182.75 | 10351.06 / 20902.72 |
| retryWaitMs | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| queueWaitMs | 696397.62 / 1462496.62 | 694586.90 / 1459897.48 | 694193.14 / 1462538.50 | 692060.65 / 1463200.66 |
| endToEndMs | 711155.04 / 1477665.06 | 717986.80 / 1479852.69 | 721882.73 / 1479888.12 | 712532.63 / 1477760.21 |

### Repairs and waits in the matched sample

| Approach | Repairs | Results with retry wait | Maximum retry wait, s | Total retry wait, s |
|---|---:|---:|---:|---:|
| A | 15 | 4 | 239.00 | 478.01 |
| B | 79 | 6 | 120.01 | 420.17 |
| C | 96 | 6 | 120.01 | 480.01 |
| D | 111 | 3 | 450.01 | 570.02 |

Service runs from worker assignment to final validation, including HTTP repairs, pacing and retry waits. HTTP total sums all awaited initial/repair/failed HTTP calls for the slot; it includes network and remote queues, not pure inference. Active pipeline subtracts deliberate pacing and retry waits from service. Local validation excludes the measured calculation operation. Queue and end-to-end are session-relative batch measurements, not single-user application latency. Offline correctness scoring and final audit-file persistence are excluded. Component percentiles do not add to total percentiles.

## Execution sessions: service median / p95, seconds

| Session | A | B | C | D |
|---|---:|---:|---:|---:|
| completion | 15.072 / 20.872 (n=209) | 15.192 / 30.782 (n=209) | 15.180 / 30.688 (n=209) | 15.229 / 30.336 (n=209) |
| continuation | 14.922 / 19.318 (n=166) | 15.200 / 31.668 (n=166) | 15.367 / 31.388 (n=166) | 15.384 / 31.693 (n=166) |
| original | 14.972 / 22.666 (n=157) | 15.121 / 31.285 (n=157) | 15.160 / 31.304 (n=157) | 15.166 / 30.630 (n=157) |

## Paired exploratory differences

Left minus right: negative means the left approach used less time. Equal weight is given to each project; 10,000 project-bootstrap resamples produce descriptive 95% intervals. There are at most ten independent project clusters. These intervals do not remove provider/worker interference or establish general causality.

| Metric | Comparison | Mean difference, ms | Descriptive 95%, ms | Matched groups |
|---|---|---:|---:|---:|
| serviceTotalMs | B-A | 1959.22 | [-194.80, 3757.00] | 532 |
| serviceTotalMs | C-B | 561.31 | [-282.88, 1407.81] | 532 |
| serviceTotalMs | D-C (arithmetic only) | 772.62 | [-1741.01, 3177.82] | 176 |
| providerRoundTripMs | B-A | 870.25 | [423.14, 1295.86] | 532 |
| providerRoundTripMs | C-B | 28.86 | [-271.01, 322.80] | 532 |
| providerRoundTripMs | D-C (arithmetic only) | 835.36 | [-158.36, 1910.67] | 176 |
| activePipelineMs | B-A | 874.93 | [427.22, 1305.12] | 532 |
| activePipelineMs | C-B | 24.67 | [-273.07, 316.79] | 532 |
| activePipelineMs | D-C (arithmetic only) | 848.27 | [-148.40, 1926.80] | 176 |

## Evidence, checks and limitations

- Physical request states: `{'returned': 2473, 'failed': 34, 'started': 9}`; statuses: `{'200': 2473, '429': 34, 'started': 9}`. Interrupted started receipts remain explicitly unverified; they are not silently relabeled as completed or assigned invented durations.
- All returned receipt tokens, including preserved orphan responses: 2,030,601. Missing usage on interrupted requests is unknown. Tokens are not verified billing.
- Passed: identity consistency for completed slots, immutable original evidence hashes, frozen generator hashes, selected provider receipts and usage, timing partitions, and independent offline correctness scoring. Full planned identity coverage passed across the three sessions. Exact uninterrupted-run gates remain abandoned and are not relabeled as passed.
- Original uninterrupted-run gate is abandoned because of host loss. The segmented verification is a replacement outcome and does not erase that limitation.
- Nine fixed paced workers used the supplied credentials. Independent organizations/quotas were asserted by the user and not verified. Quota waits, shared provider load and account/worker scheduling affect timing.
- Latency differences combine prompt generation, detection and repair policy. A can accept a semantically wrong response without repair, while contract arms may reject and repair it. A faster returned answer is not necessarily a faster correct answer; these results do not isolate validation as the cause of a timing difference.
- Dependencies were reinstalled after host loss. Continuation environment is recorded; exact equivalence to the lost environment is not established. Report sessions separately.
- Excluding interrupted and cross-session groups can omit slower requests and bias observed latency, particularly tail percentiles. The complete identity coverage does not remove that exclusion bias.
- The tasks were reused from H60. They are researcher-created public-record adaptations, not 60 organic production prompts or new untouched confirmation tasks. Original source archive was not recaptured.
- D measures assembled system output. It does not prove the model learned arithmetic. Zero observed wrong acceptance does not guarantee complete validation.
- No browser/server production journey, streaming time to first token, pure model inference, billed cost, or universal speed/accuracy improvement is measured.
- Detailed per-model, project, family, worker and session distributions, all-completed sensitivity results, and bootstrap values are in FINISHED_SUMMARY.json.

## Claims

Supported: measured response-ready harness timings and token/correctness outcomes on these tasks, settings and execution sessions. Comparisons must state their sample, waits, repair allowance and session limitation.

Not supported: HESchema always speeds up models; contract checking guarantees correctness; all observed service differences come from contracts; the study is an uninterrupted or production latency benchmark; new JSON Schema vocabulary is necessary.

## Results by model in the primary sample

| Model | Approach | N | Final correct | HTTP median / p95, s | Service median / p95, s |
|---|---|---:|---:|---:|---:|
| openai/gpt-oss-120b | A | 179 | 162 | 5.180 / 9.933 | 15.159 / 22.528 |
| openai/gpt-oss-120b | B | 179 | 161 | 5.737 / 14.045 | 15.409 / 30.782 |
| openai/gpt-oss-120b | C | 179 | 157 | 6.505 / 14.115 | 15.507 / 31.139 |
| openai/gpt-oss-120b | D | 179 | 157 | 6.248 / 14.105 | 15.755 / 31.345 |
| openai/gpt-oss-20b | A | 175 | 154 | 5.437 / 9.891 | 15.005 / 29.671 |
| openai/gpt-oss-20b | B | 175 | 142 | 6.405 / 13.870 | 15.327 / 31.910 |
| openai/gpt-oss-20b | C | 175 | 141 | 6.477 / 14.075 | 15.368 / 31.388 |
| openai/gpt-oss-20b | D | 175 | 145 | 6.862 / 15.877 | 15.636 / 31.555 |
| qwen/qwen3.8-27b | A | 178 | 169 | 5.267 / 9.043 | 14.816 / 21.847 |
| qwen/qwen3.8-27b | B | 178 | 178 | 5.666 / 10.641 | 14.867 / 30.518 |
| qwen/qwen3.8-27b | C | 178 | 177 | 4.890 / 9.680 | 14.928 / 29.867 |
| qwen/qwen3.8-27b | D | 178 | 177 | 4.710 / 9.091 | 14.811 / 23.518 |

## Verification status

1,091 local tests passed; 10 optional tests skipped; one dependency deprecation warning. Nine focused timing/resume/report tests and focused lint passed. Seven unlazy gates are met, including the new three-session completion check. Two historical completion gates remain abandoned because their original execution sessions cannot be reconstructed. No scheduled result identities remain unfinished. Nine historical incomplete physical receipts remain unknown and are disclosed.
