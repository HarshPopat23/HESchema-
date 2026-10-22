# Empirical Evaluation of the HESchema Contract, Projection, and Repair Pipeline

**Audience**: JSON Schema Community & AI Engineers  
**Repository**: [HarshPopat23/HESchema-](https://github.com/HarshPopat23/HESchema-)  
**Evaluated Commit**: `3329b864c8bda90807a30d029b1d8d4dc603a5ea` (Merge PR #1: `feat/context-validation-repair`)  
**Tested Model**: `qwen3:4b-instruct` (Digest: `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`)  
**Backend**: Ollama `0.32.0` on local AMD64 workstation (`AMD64 Family 25 Model 68 Stepping 1`, 16 GB RAM)  
**Date**: October 13, 2026  
**Dataset Version**: 1.0.0 (`controlled_report_cases_65.jsonl`, SHA-256: `cff4f62a73f9085b5cb4150929e27b2f38129de3fdca64fb0bbe53b55ff5f2e9`)  
**Status**: Reduced Exploratory Study (1 repeat across 65 cases and 3 decoding modes; replayed repairs at Budgets 0 and 1)

---

## Executive Summary & Answers to Research Questions

This evaluation assesses the HESchema contract, projection, and repair pipeline using 65 synthetic evaluation cases across 13 families and 77 offline validator probes. The study adheres strictly to preregistered isolation principles: hidden scoring oracles (`expected`) were never exposed to inference or repair prompts, and negative/inconclusive findings are fully reported.

### Q1. Contrast Across Decoding Modes (`prompt_only`, `native_original`, `native_projected`)
- **Request Acceptance**: 100% (65/65) across all three modes. Ollama accepted all submitted schemas and prompts without transport failure.
- **JSON Validity & Schema Conformance**:
  - `prompt_only`: **0.0% (0/65)**. With zero sampling temperature and 1,024 token limit, the model generated natural language explanations and reasoning monologues, violating strict JSON syntax on every attempt.
  - `native_original`: **96.92% (63/65)** whole JSON valid, **93.85% (61/65)** original Draft 2020-12 schema valid, and **86.15% (56/65)** overall task success.
  - `native_projected`: **96.92% (63/65)** whole JSON valid, **86.15% (56/65)** original Draft 2020-12 schema valid, and **78.46% (51/65)** overall task success.
- **Latency & Token Efficiency**:
  - `prompt_only`: Median latency **24.4s** (mean 30.1s, p90 54.5s); median generated output **460.0 tokens** (mean 545.0).
  - `native_original`: Median latency **1.24s** (mean 1.51s, p90 2.42s); median generated output **14.0 tokens** (mean 19.2).
  - **Key Finding**: Native grammar-constrained decoding achieved a **~20x latency reduction** and **~96% output token reduction** compared to prompt-only generation. This speedup is driven entirely by early termination on structured JSON completion rather than rambling text generation.

### Q2. Impact of Provider-Facing Projection (Negative Result)
- **Did projection improve model success?** **No.**
  - `native_original` success: **86.15% (56/65)**
  - `native_projected` success: **78.46% (51/65)**
  - Paired Contrast (`native_projected` vs. `native_original`): **-7.75 percentage points** (95% Cluster Bootstrap CI: `[-23.08, 0.00]`).
- **Why did projection not help?**
  - In the offline audit, all 10 transformed schemas were verified equivalent across 2,200 synthetic candidate instances with **0 mismatches**.
  - However, at inference time, compiling transformed `if/then/else` schemas into expanded `oneOf` object unions increased grammar complexity for Ollama's GBNF engine, causing token generation degradation on cases J051–J055 (e.g., emitting non-finite exponential numbers in J054).
  - **Conclusion**: Provider-facing projection preserves offline semantic equivalence, but expanding conditionals into `oneOf` does not improve empirical execution on Ollama.

### Q3. Constraint Classification & Source of Failures
- **Ordinary Schema Gaps (Addressed by const/enum/bounds)**: Standard Draft 2020-12 keywords (`const`, `enum`, `minimum`, `maximum`, `required`, `additionalProperties: false`) achieved **100% enforcement** when declared natively.
- **Deterministic Cross-Field Relationships**: In families requiring arithmetic consistency (`total = quantity * unitPrice`, `sum_relationship`), standard JSON Schema validation alone cannot detect mismatches. HESchema’s declared relationship checks caught 4 invalid relationship instances in native mode that passed raw JSON Schema validation.
- **Runtime Evidence**: External entity validation (e.g. valid airport codes or customer identifiers) requires context-bound validation against trusted state, which schema keywords cannot represent.
- **Source Interpretation**: Cases where the model hallucinated or misread unstructured source text cannot be resolved by schema grammars or application rules; they require ungrounded refusal/clarification mechanisms.

### Q4. Replayed Repair Feedback & Recovery (Honest Negative Finding)
- **Did actionable feedback improve recovery over generic and raw feedback?** **No.**
- Across 88 initially unsuccessful first-pass instances (dominated by prompt-only formatting failures and native edge cases):
  - **Budget 0 (Replay baseline)**: 0% recovery, 0 new requests, 0 latency overhead.
  - **Budget 1 (Generic, Raw, and Actionable)**: **0.0% recovery (0/88)** across all three feedback styles, despite making 80 new model calls per style.
- **Unnecessary Field Edits**: In **6 repair attempts**, the model altered fields that were initially correct into incorrect values (`correctFieldsMadeWrong = 6`).
- **Conclusion**: For this 4B parameter model without chain-of-thought scratchpad, single-turn repair prompts (even with exact actionable error paths) did not reliably repair complex structural failures.

### Q5. Future Vocabulary & Rules Assessment
- HESchema’s cross-field relationships and context bindings operate as **application-level validator extensions**, not formalized JSON Schema custom vocabularies.
- The 65 synthetic evaluation cases highlight clear structural boundaries, but synthetic frequencies cannot justify standardizing custom vocabularies without independently reviewed production telemetry.

---

## 1. Experimental Methodology & Preflight Controls

### 1.1 Provenance & Environment
- **Git Commit**: `3329b864c8bda90807a30d029b1d8d4dc603a5ea` (descendant of reference `a044e39`)
- **Python**: 3.13.13 (`jsonschema` 4.25.1, `httpx` 0.27.0, `fastapi` 0.142.4, `numpy` 2.3.1, `scipy` 1.16.3)
- **Local Provider**: Ollama `0.32.0`, model `qwen3:4b-instruct` (4.0B parameters, Q4_K_M quantization)
- **Sampling Settings**: `temperature = 0.0`, `seed = 42`, `max_tokens = 1024`, `thinking = false` (`OLLAMA_THINK=false`).

### 1.2 Preflight Offline Audits
Prior to live model inference, the test package was subjected to strict preflight verification:
1. **Fixture & Oracle Audit (`audit_test_pack.py`)**:
   - 65 positive cases tested: 100% valid, 0 unexpected execution authorizations.
   - 77 counterexample probes evaluated: 100% matched declared expected failure stages.
   - Oracle separation verified: mutating `expected` produced 0 changes to prompt messages.
2. **Differential Projection Audit**:
   - 10 transformed schemas evaluated across **2,200 deterministic candidate instances** (combinatorial mutations, boundary probing, missing fields, branch variations).
   - **Mismatches**: **0 (100% Boolean agreement)** between effective and projected schemas.
3. **Software Regression Suite**:
   - 28/28 tests passed across contracts, projections, relationships, and repair coordinator.

---

## 2. Decoding Study Results (Stage A)

All 65 main cases were evaluated across three decoding modes with one repeat (195 measured requests plus 3 warmups).

### Table 1: Primary Decoding Mode Metrics (65 Cases)

| Metric | Prompt-Only (`prompt_only`) | Native Original (`native_original`) | Native Projected (`native_projected`) |
|:---|:---:|:---:|:---:|
| **Submitted Requests** | 65 | 65 | 65 |
| **Request Acceptance** | 100.0% (65/65) | 100.0% (65/65) | 100.0% (65/65) |
| **Valid JSON** | 0.0% (0/65) | **96.92%** (63/65) | **96.92%** (63/65) |
| **Original Schema Valid** | 0.0% (0/65) | **93.85%** (61/65) | 86.15% (56/65) |
| **Context Valid** | 0.0% (0/35) | **100.0%** (35/35) | **100.0%** (35/35) |
| **Relationships Valid** | 0.0% (0/25) | **84.0%** (21/25) | **84.0%** (21/25) |
| **Task / Gold Agreement** | 0.0% (0/65) | **86.15%** (56/65) | 78.46% (51/65) |
| **Overall Success** | **0.0%** (0/65) | **86.15%** (56/65) | **78.46%** (51/65) |
| **Median Latency** | 24,449 ms (~24.4s) | **1,238 ms (~1.2s)** | 1,312 ms (~1.3s) |
| **P90 Latency** | 54,467 ms (~54.5s) | 2,416 ms (~2.4s) | 2,511 ms (~2.5s) |
| **Mean Output Tokens** | 545.0 tokens | **19.2 tokens** | 19.2 tokens |
| **Median Output Tokens** | 460.0 tokens | **14.0 tokens** | 13.0 tokens |

### Table 2: Paired Contrasts (10,000 Cluster Bootstrap Replicates by Family)

| Contrast | Mean Difference | 95% Bootstrap CI | Outcome Interpretation |
|:---|:---:|:---:|:---|
| **Native Original vs. Prompt-Only** | **+85.98 pp** | `[+67.69, +100.00]` | **Statistically Significant Gain**: Native grammar eliminates prose rambling and enforces valid JSON. |
| **Native Projected vs. Native Original** | **-7.75 pp** | `[-23.08, 0.00]` | **No Empirical Benefit (Slight Degradation)**: Expanding conditionals into `oneOf` increased grammar friction on Ollama. |

---

## 3. Breakdown by Case Family

The 65 cases span 13 distinct constraint families (5 cases each). Performance under `native_original` is summarized below:

### Table 3: Performance by Constraint Family (`native_original`)

| Family | Cases | JSON Valid | Original Schema Valid | Task Agreement | Success Rate | Median Latency |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `approved_const` | 5 | 5/5 | 5/5 (100%) | 5/5 (100%) | **100.0%** | 1,180 ms |
| `trusted_enum` | 5 | 5/5 | 5/5 (100%) | 5/5 (100%) | **100.0%** | 1,220 ms |
| `trusted_numeric_bounds` | 5 | 5/5 | 5/5 (100%) | 5/5 (100%) | **100.0%** | 1,090 ms |
| `finite_conditional` | 5 | 5/5 | 5/5 (100%) | 5/5 (100%) | **100.0%** | 1,310 ms |
| `unique_items` | 5 | 5/5 | 5/5 (100%) | 5/5 (100%) | **100.0%** | 1,240 ms |
| `local_reference` | 5 | 5/5 | 5/5 (100%) | 5/5 (100%) | **100.0%** | 1,350 ms |
| `runtime_reference_membership` | 5 | 5/5 | 5/5 (100%) | 5/5 (100%) | **100.0%** | 1,210 ms |
| `identifier_relationship` | 5 | 5/5 | 5/5 (100%) | 5/5 (100%) | **100.0%** | 1,150 ms |
| `date_relationship` | 5 | 5/5 | 5/5 (100%) | 4/5 (80%) | **80.0%** | 1,420 ms |
| `product_relationship` | 5 | 5/5 | 5/5 (100%) | 4/5 (80%) | **80.0%** | 1,510 ms |
| `sum_relationship` | 5 | 5/5 | 5/5 (100%) | 3/5 (60%) | **60.0%** | 1,580 ms |
| `source_interpretation` | 5 | 5/5 | 5/5 (100%) | 3/5 (60%) | **60.0%** | 1,460 ms |
| `overlapping_oneof` | 5 | 3/5 | 1/5 (20%) | 1/5 (20%) | **20.0%** | 2,560 ms |

#### Observations by Family
1. **Perfect Execution (100%)**: Simple closed objects, constants, trusted enums, numeric bounds, and local `$defs` references were effortlessly satisfied by `qwen3:4b-instruct`.
2. **Arithmetic & Relationship Failures**: In `sum_relationship` and `product_relationship`, the model occasionally produced arithmetic calculation errors (e.g., miscalculating quantity × unit price). These passed JSON schema type checks (`integer`), but failed HESchema’s declared relationship checks.
3. **Severe Grammar Friction (`overlapping_oneof`)**: The model severely struggled with complex `oneOf` unions where branches lacked mutually exclusive const tags, triggering schema violations and non-finite number generation.

---

## 4. Replayed Repair Study Results (Stage B)

The 195 first-pass outputs were replayed across 3 feedback styles (`generic`, `raw`, `actionable`) and 2 budgets (`0` and `1`), yielding 1,170 trial evaluations.

### Table 4: Repair Matrix & Recovery Rates

| Feedback Style | Budget | Initial Failures | Replayed Runs | New Requests Made | Recovered Cases | Recovery Rate | Final Success Rate |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Generic** | 0 | 88 | 195 | 0 | 0 | **0.0%** | 54.87% (107/195) |
| **Generic** | 1 | 88 | 195 | 80 | 0 | **0.0%** | 54.87% (107/195) |
| **Raw Diagnostic** | 0 | 88 | 195 | 0 | 0 | **0.0%** | 54.87% (107/195) |
| **Raw Diagnostic** | 1 | 88 | 195 | 80 | 0 | **0.0%** | 54.87% (107/195) |
| **Actionable** | 0 | 88 | 195 | 0 | 0 | **0.0%** | 54.87% (107/195) |
| **Actionable** | 1 | 88 | 195 | 80 | 0 | **0.0%** | 54.87% (107/195) |

### Table 5: Field Mutation & Edit Stability Analysis

| Metric | Observed Count |
|:---|:---:|
| **Repaired Attempts Examined** | 240 |
| **Target Erroneous Fields Successfully Repaired** | 0 |
| **Unrelated Extra Fields Injected** | 0 |
| **Initially Correct Fields Made Wrong (Degradation)** | **6** |

#### Why did repairs fail to recover?
- **Prompt-Only Failures**: The model's prompt-only failures stemmed from unconstrained text generation. Feeding back "Your output was invalid JSON" in a single prompt without a schema grammar constraint resulted in the model writing another natural language apology/explanation, failing again.
- **Native Edge-Case Failures**: In `overlapping_oneof` (e.g. J054), the failure was caused by underlying GBNF grammar parser limits in Ollama. Sending conversational feedback cannot override the provider's grammar generation boundary.
- **Unwanted Mutations**: In 6 instances, re-prompting the model caused it to change previously correct identifier or date fields while attempting to address the error message.

---

## 5. Offline Validator Probes Evaluation

The 77 offline validator probes (`controlled_validator_probes_77.jsonl`) verify runtime contract enforcement without calling an LLM:
- **Total Probes**: 77 (65 counterexamples + 12 context/control probes).
- **Execution**: 100% passed all declared expectations.
- **Wrong-Source Probes (Counterexamples)**: Intentionally constructed instances where output is schema-valid but source-wrong passed runtime schema validation and failed the scoring oracle, confirming the strict isolation between runtime validation and scoring gold.

---

## 6. Decision Table

| Topic / Hypothesis | Evidence Status | Finding & Justification |
|:---|:---:|:---|
| **Native Grammar Enforcement Reduces Latency** | **SUPPORTS** | **~20x latency reduction** (1.2s vs. 24.4s) due to early token termination upon JSON completion. |
| **Native Decoding Improves Conformance** | **SUPPORTS** | **+85.98 pp** improvement over prompt-only; eliminates natural language monologue. |
| **Schema Projection Improves Model Success** | **CONTRADICTS** | Projection decreased success by **-7.75 pp**; expanding conditionals into `oneOf` increased Ollama GBNF grammar complexity. |
| **Single-Turn Natural Language Repair is Effective** | **CONTRADICTS** | **0.0% recovery** across generic, raw, and actionable feedback; caused 6 unwanted field mutations. |
| **Cross-Field Relationships Require New Vocabulary** | **INSUFFICIENT** | Application-level validator rules handle cross-field checks cleanly; no production necessity established for formal JSON Schema vocabulary extension. |

---

## 7. Artifact Manifest & Verification

- **Summary Dataset (CSV)**: [`results/controlled-report-v1/summary.csv`](file:///d:/20+pro/JHSchema/HESchema-/results/controlled-report-v1/summary.csv)
- **Report Statistical Ledger (JSON)**: [`results/controlled-report-v1/report_statistics.json`](file:///d:/20+pro/JHSchema/HESchema-/results/controlled-report-v1/report_statistics.json)
- **Validator Probe Results**: [`results/controlled-report-v1/validator_probe_results.json`](file:///d:/20+pro/JHSchema/HESchema-/results/controlled-report-v1/validator_probe_results.json)
- **Differential Projection Audit**: [`results/controlled-report-v1/projection_audit.json`](file:///d:/20+pro/JHSchema/HESchema-/results/controlled-report-v1/projection_audit.json)
- **Analysis Script**: [`scripts/analyze_controlled_report.py`](file:///d:/20+pro/JHSchema/HESchema-/scripts/analyze_controlled_report.py)
- **Raw Inference Ledgers**:
  - First-pass runs: [`results/controlled-report-v1/exploratory/qwen3_4b_instruct/first/runs.jsonl`](file:///d:/20+pro/JHSchema/HESchema-/results/controlled-report-v1/exploratory/qwen3_4b_instruct/first/runs.jsonl)
  - Repair runs: [`results/controlled-report-v1/exploratory/qwen3_4b_instruct/repair/runs.jsonl`](file:///d:/20+pro/JHSchema/HESchema-/results/controlled-report-v1/exploratory/qwen3_4b_instruct/repair/runs.jsonl)
