# Non-arithmetic confirmation on fresh public records

**The scheduled study is incomplete.** There are **424/540 completed slots**, **211 matched pairs**, **30 tasks** and **6 source projects**.

**Recording remains incomplete at the physical-request level.** Execution interruptions may have lost up to 16 calls across in-flight slots. Their responses and usage are unknown. Completed saved slots were retained; the remaining schedule was resumed. Consequently, “first” below means the first **recorded** generation, and token figures are observed usage, not verified totals for every call or actual billed cost.

**Execution block:** Execution process cannot be resumed: tool reports network policy blocks https://api.groq.com:443. No credential change or network bypass attempted. The saved checkpoint contains 424 of 540 scheduled slots; 116 remain incomplete. This is a partial confirmation report, not a completed study.

## What was tested

The previous pilot reused extraction/aggregation tasks from its earlier study. This pack uses 30 newly authored tasks with real, byte-preserved public records from Node.js Release, endoflife.date, SPDX, IANA, Prometheus Operator and Homebrew. Ten tasks test date ordering, ten exact identifier matching, and ten trusted-list membership. They are researcher-created adaptations, not naturally collected production prompts or upstream-authored contracts.

A baseline exposure audit hashed 315 tracked research/benchmark/test files and compared 653 prior instruction hashes and 204 prior context hashes. No exact overlap was found for the selected instructions/context records or inspected source identifiers. SchemaStore was excluded because earlier research had already examined it. “Untouched” is limited to the inspected local studies; public model-pretraining exposure and unseen external work are unknown.

FULL sends the projected schema, approved bindings and trusted facts. COMPACT sends the original schema, binding locations and the same trusted facts. Both retain identical full contract checks after generation. There is **no ordinary-schema-only generation arm**.

The schedule uses three Groq models, three repeats, prompt-only generation, temperature zero, a 2,048-token output budget and at most one returned repair per slot. No application calculations, output cleanup, provider schema enforcement or oracle feedback are used. The seed randomizes the schedule; Groq does not receive a generation seed through this adapter. GPT OSS requests low reasoning effort; Qwen uses its provider-supported default.

The cases/protocol/source snapshots were sealed before study inference. The semantic oracle uses separate date, record-equality and membership logic, accepts all valid alternatives, and runs only after bounded generation/repair. It is independently implemented semantic checking, not independent human review or a second independent JSON Schema implementation.

## Matched results

| Measure | FULL | COMPACT |
|---|---:|---:|
| Correct first recorded answer | 97.63% (206/211) | 88.63% (187/211) |
| Correct final recorded answer | 100.00% (211/211) | 93.84% (198/211) |
| Initially wrong matched slots recovered | 5/5 | 11/24 |
| Observed tokens, including returned repairs/checkpoints | 103,997 | 109,563 |
| Observed mean tokens per matched slot | 492.88 | 519.26 |
| Wrong responses accepted by contract | 0 | 0 |
| Correct responses rejected by contract | 0 | 0 |
| Wrong responses accepted by ordinary shape schema, offline counterfactual | 5 | 3 |
| Median latest-checkpoint coordinator time | 6.27 s | 6.32 s |

COMPACT changed recorded total token usage by **+5.35%** relative to FULL. This is a matched, observed-token comparison; interruption losses prevent a complete cost accounting. The earlier pilot’s 20.65% token reduction is not assumed to transfer to these new tasks.

**The earlier token saving did not replicate in this recorded sample.** COMPACT also had lower final recorded correctness. These results support keeping prompt modes optional and testing them on the intended workflow; they do not establish universal accuracy, cost or speed effects.

### By model

| Model | Matched pairs | FULL first / final correct | COMPACT first / final correct |
|---|---:|---:|---:|
| `openai/gpt-oss-120b` | 68 | 68 / 68 | 68 / 68 |
| `openai/gpt-oss-20b` | 69 | 64 / 69 | 66 / 69 |
| `qwen/qwen3.8-27b` | 74 | 74 / 74 | 53 / 61 |

### By relationship family

| Family | Matched pairs | FULL first / final correct | COMPACT first / final correct |
|---|---:|---:|---:|
| date ordering | 68 | 68 / 68 | 49 / 55 |
| identifier matching | 74 | 74 / 74 | 74 / 74 |
| list membership | 69 | 64 / 69 | 64 / 69 |

## Failure analysis

Across all recorded returned responses, **32** were Markdown-fenced payloads; **32** contained semantically correct payloads inside the fence. This is a post-hoc diagnostic only: they remain invalid whole JSON and are never converted into successes. A date-task formatting failure must not be relabeled as an incorrect date-order relationship.

Observed failure labels overlap and describe returned responses, not independent tasks:

- `json_syntax`: 32 returned responses.
- `output_empty`: 2 returned responses.
- `relationship_violation`: 8 returned responses.
- `trusted_membership`: 8 returned responses.

Those semantic failures cover **2 task records**, **1 source project(s)** and **1 model(s)**. Repeats of one task do not establish cross-workflow reproducibility.


Semantic relationship failures were observed in these recorded outputs:

- `confirmation-22`, `openai/gpt-oss-20b`, `full`, repeat 0, attempt 0.
- `confirmation-21`, `openai/gpt-oss-20b`, `full`, repeat 0, attempt 0.
- `confirmation-21`, `openai/gpt-oss-20b`, `compact`, repeat 0, attempt 0.
- `confirmation-21`, `openai/gpt-oss-20b`, `compact`, repeat 2, attempt 0.
- `confirmation-22`, `openai/gpt-oss-20b`, `full`, repeat 1, attempt 0.
- `confirmation-22`, `openai/gpt-oss-20b`, `full`, repeat 2, attempt 0.
- `confirmation-21`, `openai/gpt-oss-20b`, `full`, repeat 1, attempt 0.
- `confirmation-21`, `openai/gpt-oss-20b`, `compact`, repeat 1, attempt 0.
- `date_before`: 0 invalid of 125 evaluated checks. Unevaluated checks are not counted as passes.
- `equals`: 0 invalid of 148 evaluated checks. Unevaluated checks are not counted as passes.
- `reference_member`: 8 invalid of 544 evaluated checks. Unevaluated checks are not counted as passes.

See [all recorded failures](evidence/failures.jsonl) and [exact final content for every recorded return](evidence/responses.jsonl). Neither successful answers nor failures were selected away. Earlier private-study prompts/responses are excluded; reasoning, credentials and HTTP headers are not published.

## Consistency and uncertainty

Three repeats measure consistency; they are not three independent tasks. Outcomes are averaged within each task across models/repeats, then whole source projects are resampled for the descriptive bootstrap. Six clusters and three shared instruction templates give limited statistical resolution.

- First recorded: COMPACT wins 3, FULL wins 22, ties 186 among paired trials; mean task difference -9.25 percentage points, descriptive 95% project-bootstrap interval [-21.08, 0.00] percentage points.
- Final recorded: COMPACT wins 0, FULL wins 13, ties 198 among paired trials; mean task difference -6.22 percentage points, descriptive 95% project-bootstrap interval [-13.91, 0.00] percentage points.

These are dependent paired trials, not independent sample counts for a significance test. A zero-width empirical interval at ceiling does not establish population equivalence, zero error probability or universal validator safety.

## Validation controls and operational history

All **190 controls** pass: **100 enumerated valid alternatives**, **60 structurally valid semantic corruptions**, and **30 malformed-JSON controls**. Corruptions are synthetic probes excluded from live inputs. Ordinary shape schemas accepted the 60 semantic corruptions; the independent oracle and contract checks rejected them. Many finite allowed choices can also be expressed with source-derived ordinary `enum`/`const` constraints. These controls do not demonstrate that new vocabulary is necessary.

Session 1 stopped after 185 completed slots when its per-worker quota retry budget was exhausted. Session 2 increased minimum worker spacing from 10 to 20 seconds and reached 198 completed slots before workspace interruption. Session 3 retained the 20-second pacing and the same frozen cases, runtime hashes and generation settings. Its first pending quota-failed slot retained its prior credential. A sanitized response observer records quota categories without provider error bodies. It stopped at 413 completed slots after exhausting its bounded quota retry allowance. Session 4 increased worker and per-provider call spacing to 30 seconds, including repairs, and saved 424 completed slots before its process could no longer be resumed under the current network policy. No new quota events were recorded in session 4. The second interruption adds a conservative upper bound of eight possibly unrecorded calls; the two interruptions together allow up to sixteen.

Session histories preserve original configs, summaries, journal hashes and relative worker mappings. Credential pools were authorized in advance; workers did not fail over to another credential in reaction to an individual quota error. Limits need not be independent across keys. Per-worker quota retries are bounded per invocation, with 120-second waits. Model response IDs/fingerprints are retained when returned; fixed model names do not guarantee unchanged hosted weights across days.

The journal records **462 request attempts** and **453 returned generations**. Additional interruption calls are unknown. The coordinator records provider client response time, validation, calculation, coordinator work and retry phases. Dispatch pacing and quota waits remain separate. Replayed initial responses are not billed again as new observed tokens or provider latency. The latest-checkpoint median can omit an earlier checkpoint’s work and is not total user-visible time. Parallel throughput, client response time and hosted inference time are different measurements. **This run does not establish a speed improvement or actual billed savings.**

## Supported conclusions and limits

- The pack broadens local testing beyond the previously reused arithmetic, extraction and aggregation tasks, with genuine public source records and multiple acceptable answers.
- Contract decisions can be independently checked against recorded output and the declared source facts. Observed zero wrong acceptance/rejection is finite-sample evidence only.
- Formatting failures and semantic relationship failures must remain separate. Prompt compactness alone cannot be assumed to improve accuracy, token use or latency.
- Keep FULL available and retain COMPACT as an opt-in option. Do not change prompt defaults or weaken strict JSON validation based only on this small study.
- No ordinary-schema generation arm, organically collected production prompts, independent human review, pretraining-contamination guarantee or complete physical-request record exists here. All live tasks are answerable; missing-context workflows and full Kubernetes authorization are not tested.
- Simple lifecycle intervals, literal identifier matching and finite membership do not cover time zones, complex joins, normalization, wildcard authorization or all cross-field rules. Repeated records/templates within projects limit generalization.
- The observed categories and controls do not yet establish that relationship failures recur broadly enough to justify a custom JSON Schema vocabulary. Ordinary schema constraints and application checks remain alternatives.

Next, use a separately frozen, untouched set of harder application workflows and an explicit ordinary-schema comparator if the research question is validator or generation superiority. Investigate durable per-request logging before another long run. Do not tune the current pack after seeing its failures.

## Reproduce and inspect

See [the frozen protocol](protocol.json), [source attribution](SOURCES.md), [exposure audit](exposure.json), [input freeze](freeze.json), [machine-readable results](evidence/summary.json) and [public artifact manifest](evidence/manifest.json).

```sh
python -m pip install -e '.[dev]'
python -m heschema.confirmation_run
python scripts/verify_confirmation_evidence.py
python scripts/write_confirmation_report.py
```

These checks need no model credentials or new generation. Live re-execution requires authorized credentials and is a new run, not reconstruction of the same hosted-model responses.
