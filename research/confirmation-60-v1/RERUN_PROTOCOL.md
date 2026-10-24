# H60 independent-oracle replication

The original 2,160 saved slots contain a scoring defect: `validate_contract.success` requires an active source binding, while membership-only tasks have relationships without bindings. Acceptance is not a scientific correctness oracle. The independent checker in `scripts/rescore_confirmation60.py` evaluates the task conditions without calling HESchema's validator, rule evaluator or calculation implementation.

## Scope and controls

- Reuse the same 60 authored public-record adaptations, ten projects, six families, three models, three repetitions and A/B/C/D arms. This is a replication of exposed tasks, not untouched-task confirmation or organic production traffic.
- Preserve the historical raw responses. Publish offline rescoring separately from new inference.
- Keep the historical prompts, facts, generation settings and single detector-triggered repair allowance. D changes the generated schema only for eligible declared arithmetic rules; otherwise it follows C.
- Freeze task bytes, Python implementation hashes and schedule in the run manifest before issuing inference. No expected answers enter generation or feedback.
- Score ordinary schema conformance separately from independent task correctness. D correctness refers to assembled system output; it does not show improved LLM arithmetic.
- Use a short engineering pilot outside the replication result directory. The pilot reuses H60 inputs and is not evidence of generalization.
- Preserve durable request receipts before sending and durable final content/usage before evaluating each response. Record physical retries, provider status, response ID, model and finish reason. Omit credentials, headers and private reasoning.
- Stop on nonretryable provider errors or retry-budget exhaustion. Never label a provider failure as a completed successful trial. Automatic resume is disabled until incomplete requests and pending repairs are inspected.
- Use each supplied credential through its own paced worker. A successful authentication check does not verify organization independence. Respect provider throttling; keys do not guarantee multiplied quota.

## Analysis and claims

Report schedule coverage, receipt coverage, parsed JSON, first/final independent correctness, wrong acceptance and correct rejection. Separate tokens for initial/repair physical returns using receipt usage. Show results by arm, model, project and family; paired trial differences are descriptive, not independent-task sample sizes. Bootstrap whole projects when reporting uncertainty; ten clusters still provide limited resolution.

Provider round-trip duration includes HTTP/network time. The rerun does not independently instrument provider-internal compute, local validation and every pacing/backoff component. Do not claim a controlled latency improvement. Receipt timestamps and provider durations permit auditing requests and wait gaps, but are not a complete user-visible latency decomposition.

The source archive referenced by the original task document is not present in this checkout. These runs reuse the frozen supplied facts; they do not recapture or independently certify the original public response bytes. Billing is not verified. Three repeats and model/arm combinations do not create 2,160 independent tasks.

## Engineering checks before inference

Independent oracle: 61 tests exercise all 60 references, missing-field controls, family-specific incorrect values, legitimate membership alternatives, strict JSON and eligible application calculations. Clean-install dependency shortcomings and unrelated lint defects remain outside this experiment-only change. The full suite passes after explicitly installing its missing async and PostgreSQL test dependencies.

The 12-slot engineering pilot completed and each initial/repair response matched one durable receipt. It used the same protocol but a separate output directory and is excluded from the replication statistics. Two rate-limited physical requests were retained and successfully retried.

Historical reports must be marked superseded and linked to the independent rescore. Do not transform lower wrong acceptance into higher generation accuracy: those are different outcomes. Do not infer the necessity of new JSON Schema vocabulary from checks conventional application code already performs.
