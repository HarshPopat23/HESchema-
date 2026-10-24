# H60 latency protocol — 24 October 2026

This is a latency replication on the existing 60 H60 public-record adaptations, not new production tasks. Base application revision: 60f5f831594f4a3e169f30959f85ea8b9d0ce1e8. Generation code, task bytes and randomized schedule are hashed before inference.

## Fixed design

- Nine concurrent workers, each using one supplied credential. Successful requests establish credential access, not independent organizations or multiplied quotas.
- Same 60 tasks, three models, three repeats and four generation/checking approaches as the previous H60 study: 2,160 initial slots, at most one detector-triggered repair per slot.
- Prompt-only generation, temperature zero, maximum 2,048 completion tokens. Seed 20261024 randomizes the schedule, not hosted model generation.
- D uses application calculation only for declared arithmetic cases; otherwise its messages and validation match C. Correctness is independently scored offline.
- Each worker reuses its HTTP client and schema engine. No result cache, manual output cleanup or oracle feedback is used.
- A separate 12-task engineering pilot contains two tasks per family, one model per task and all four arms: 48 slots. It reuses existing tasks solely for engineering validation and is excluded from main results.
- Per-worker request-start pacing is 15 seconds. Retryable provider/network failures are retained and retried with at least the provider's requested wait or the configured backoff, up to twelve physical attempts. Nonretryable errors stop the run. Automatic resume is disabled to avoid blindly repeating successful generations.

## Disjoint timing

All intervals use Python's monotonic high-resolution clock in one process.

1. `queueWaitMs`: batch enqueuing to worker assignment, including batch backlog. It is not intrinsic model latency.
2. `pacingWaitMs`: actual deliberate request-spacing waits.
3. `retryWaitMs`: actual deliberate waits after retryable physical failures.
4. `providerRoundTripMs`: total awaited HTTP durations, including unsuccessful attempts. Includes client/network/remote queueing and execution; excludes decoding and receipt persistence after the await.
5. `applicationCalculationMs`: the calculation implementation's existing `computeMs` measurement, summed across evaluations.
6. `localValidationMs`: entire detector evaluation minus the application calculation timer. Includes parsing, source checks, schema checks and remaining calculation assembly/validation work.
7. `otherMs`: measured service total minus the five disjoint service components above. Includes prompt/feedback preparation, processing and receipt persistence/readback.

`serviceTotalMs` runs from worker assignment to the final detector decision, including repairs. `endToEndMs = queueWaitMs + serviceTotalMs`. Final slot audit-file persistence and offline oracle scoring are outside that response-ready boundary. This is a measured harness boundary, not an instrumented browser/API/authentication/database user journey. Component medians and p95 values need not add to the total median or p95.

## Evidence and analysis

Physical requests are durably recorded before sending. Returned content, usage, provider ID, resolved model and finish reason are persisted and read back before evaluation. Keys, headers and private reasoning are omitted. A separate atomic slot result avoids a shared append-only index as the only completion record.

Verification requires every scheduled slot exactly once, terminal request states, matching selected receipt identities, finite nonnegative timings, additive timing partitions and matching summed HTTP attempt durations. The independent task oracle is applied only after measurement. A missing or incomplete artifact is a verification failure, not an inferred success.

Report median and nearest-rank p95 by arm and model, alongside first/final correctness, observed tokens and wrong acceptance. Preserve failures rather than reporting successful responses only. Separate request count, slots and independent tasks. Nine-worker interference, account quotas and provider load limit causal attribution. No universal speed improvement, pure inference time, billed-cost saving or production SLO is established by this study.

The original H60 source snapshot archive remains unavailable in this checkout; the supplied source facts are reused rather than independently recaptured. Publication of raw artifacts to GitHub is outside this report-only task and remains subject to the earlier explicit-publication requirement. This task does not retry that blocked publication.
