# HESchema Main Study: Locked Comparison Protocol

**Version:** 1.0 (Frozen at 2026-10-18)  
**Study Hash:** `f140699197d823a39ffbd614499ff5b8c628f6fb64d9a306aaa1ce8e89eb15e2`  
**Ordered Case Array SHA-256:** `ab558fabd054f061fe2cc2425f84ea51c6b1fd1043a943697a8f06c4514cec05`  
**Repository Anchor Commit:** `c405078eb59aa5179ff004ce7efced4f37b34f8b`  

---

## 1. Research Question

Does expressing the same task rules as a HESchema contract, backed by approved context facts and context-projected schemas, improve:
1. First-pass task correctness.
2. Final correctness within an equal repair budget (max 1 repair).
3. Detection of incorrect outputs (reducing false acceptances).
4. Recovery from initial rejections.
5. End-to-end latency and token efficiency.

---

## 2. Experimental Arms

### Main Arm A: Ordinary JSON Schema
- **Prompt:** Exact case prompt + frozen `context.data` source facts.
- **Schema:** Standard Draft 2020-12 `contract.schema`.
- **Mode:** Prompt-only generation (no provider-enforced JSON schema, no tools).
- **Detector:** Strict JSON parsing and Draft 2020-12 schema validation.
- **Repair Allowance:** 1 repair request if rejected by detector.
- **Judge:** Common independent correctness oracle.

### Main Arm B: Contract Plus Approved Context
- **Prompt:** Same exact case prompt + same frozen `context.data` source facts.
- **Schema:** Context-projected `effective_schema` produced by HESchema + declared machine-readable relationships.
- **Mode:** Same prompt-only generation.
- **Detector:** Strict JSON parsing + effective schema validation + approved context bindings + declared relationship rule evaluation (`evaluate_rules`).
- **Repair Allowance:** 1 repair request if rejected by detector.
- **Judge:** Common independent correctness oracle.

### Optional Control Arms
- **Control C (Projected Ordinary Schema):** Same projected schema as Arm B, but omitting relationship rules. Validates using schema only.
- **Control D (Ordinary Generation + Application Checks):** Same prompt as Arm A, but validates using both schema and relationship checks.

---

## 3. Strict Parsing & Independent Oracle

- Strict JSON:
  - Exactly one JSON object, bounded by `{ ... }`.
  - Rejection of Markdown code fences, prose, and trailing text.
  - Rejection of duplicate object keys, NaN, and Infinity.
- Independent Oracle:
  - Completely reconstructs the expected JSON object from `context.data` without relying on HESchema PASS/FAIL verdicts.
  - Compares candidate values with booleans distinct from numbers, arrays order-sensitive, and object keys order-insensitive.

---

## 4. Execution Rules & Randomization

- Randomization Seed: `20261017`
- The `(case_id, model_id, repeat)` tuples are shuffled once.
- Arm order (A vs B) is randomized within each matched tuple.
- Execution Concurrency: 1 (to prevent resource contention and capture true latency).
- Resumability: Append-only transaction logging via `requests.jsonl`, `responses.jsonl`, `attempts.jsonl`, and `checkpoints.json`.
