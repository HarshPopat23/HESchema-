# HESchema latency replication — 24 October 2026

The completed study covers **2,160 selected results** on 60 reused public-record adaptations from ten projects, three models, three repeats and four approaches. They are not 2,160 independent tasks or fresh production prompts.

The primary comparison uses **532 complete matched groups (2,128 results; 532 per approach)**. Eight groups affected by interrupted requests or split across execution sessions are excluded. All 540 groups remain in secondary correctness/token summaries.

| Approach | Final independently correct | Wrong answers accepted | Mean total tokens | Median HTTP total | Median service total |
|---|---:|---:|---:|---:|---:|
| Ordinary schema | 485/532 (91.17%) | 42 | 636.1 | 5.283s | 14.979s |
| FULL contract | 481/532 (90.41%) | 0 | 1146.0 | 5.907s | 15.157s |
| COMPACT contract | 475/532 (89.29%) | 0 | 946.4 | 6.064s | 15.189s |
| Selective calculations | 479/532 (90.04%) | 0 | 988.5 | 6.017s | 15.243s |

## Supported observations

- COMPACT used **17.42% fewer total tokens than FULL**, including returned repair usage, in this matched sample.
- No latency improvement was demonstrated: COMPACT's median HTTP total was **6.064s**, compared with **5.907s** for FULL. Their paired exploratory interval includes no difference.
- Contract approaches accepted **zero observed wrong final answers**, versus **42** with ordinary schema validation. They did not improve aggregate independent correctness. Zero observed wrong acceptance is not a guarantee.
- D computes only declared arithmetic relationships. Its correctness is assembled system correctness, not improved model arithmetic. This run does not justify enabling calculations universally.

## Boundaries and limitations

HTTP total sums awaited HTTP durations for a slot, including repairs and failed attempts. It includes client/network and remote queuing; it is not pure inference time or time to first token. Service total also includes deliberate pacing, retry waits and local work. The nine concurrent workers used a 15-second request-start interval per worker. Component medians and percentiles do not add.

The run spans three sessions (635 + 680 + 845 completed results) after host loss and a later network-policy stop. Three saved initial responses were reused. Their whole groups are excluded from primary latency. Nine historical physical receipts remain without terminal evidence; their missing duration and usage are not invented. Exclusions can bias tail latency. Independent credential organizations were not verified.

The earlier replication's **19.53%** token reduction remains a separate historical result; it must not be pooled with this run's **17.42%**. The earlier synthetic native-decoding comparison also uses a different model, hardware and baseline and does not establish a general HESchema speedup.

No universal accuracy or speed improvement, guaranteed validation, verified billed savings, production SLO or need for new JSON Schema keywords is established. Earlier offline conventional-check replay showed that application checks could detect the same semantic failures; that replay was not newly executed in this latency study.

## Evidence and reproduction

- [Detailed report](../../research/latency-20261024/HESchema_Latency_Finished_Report.md)
- [Aggregate results by model, project, family, session and worker](../../research/latency-20261024/FINISHED_SUMMARY.json)
- [Protocol](../../research/latency-20261024/PROTOCOL.md), [verification](../../research/latency-20261024/VERIFICATION.md) and [publication status](../../research/latency-20261024/PUBLICATION_STATUS.md)
- [Timing definitions](../latency-measurements.md)

Raw receipts are preserved privately and are not part of this documentation commit. Hashes and aggregate results alone do not enable independent response replay from the repository. This is disclosed rather than presented as fully public reproducibility. Generation code and regression tests are included; running them does not reconstruct missing historical responses.
