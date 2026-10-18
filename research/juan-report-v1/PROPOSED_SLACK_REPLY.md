# Proposed Draft Slack Reply to Juan Cruz Viotti

*(Draft only; do not send without user review)*

---

Hi Juan,

We completed an empirical evaluation of the HESchema contract, projection, and repair pipeline against your 65 test cases and 77 validator probes using a local Ollama deployment (`qwen3:4b-instruct`, zero temperature, seed 42, 1024 token ceiling). 

The full report is compiled in `HESchema_Juan_Controlled_Report.md`, and the dataset/summary metrics are in `results/juan-report-v1/summary.csv`.

Here are the key findings answering your five research questions:

1. **Native Grammar vs. Prompt-Only (Q1)**:
   - **Native grammar decoding achieved an ~86 pp accuracy improvement** over prompt-only (86.15% vs. 0.0% task success). Without grammar constraints, the model emitted natural language preambles and explanations that failed strict JSON parsing on every attempt.
   - **~20x Latency Reduction**: Native decoding reached median latency of **1.24s** (14 output tokens) vs. **24.4s** (460 output tokens) for prompt-only, as grammar enforcement terminates immediately upon completing the structured JSON object rather than exhausting the token cap with natural language prose.

2. **Provider-Facing Projection (Q2 - Negative Result)**:
   - While our offline differential audit confirmed exact semantic equivalence across 2,200 synthetic candidate instances (0 mismatches), **live projection did not help and slightly degraded performance** (-7.75 pp, 78.46% vs. 86.15% success).
   - Transforming `if/then/else` conditionals into expanded `oneOf` object branches increased schema grammar complexity for Ollama's GBNF engine, causing severe token degradation on overlapping union cases (e.g. non-finite number generation in J054).

3. **Constraint Classification (Q3)**:
   - Standard Draft 2020-12 constraints (`const`, `enum`, `minimum`, `maximum`, `required`, `additionalProperties: false`) were 100% enforced natively.
   - Cross-field arithmetic consistency (`total = quantity * unitPrice`) and external entity membership required HESchema’s declared relationship checks and context bindings; standard JSON Schema alone cannot detect these discrepancies.
   - Hallucinations and source text ambiguities cannot be resolved by schemas or application rules; they require conservative refusal/clarification mechanisms.

4. **Replayed Repair Recovery (Q4 - Negative Result)**:
   - Replaying the 88 first-pass failures across Generic, Raw, and Actionable feedback with 1 retry yielded **0.0% recovery** across all three styles, while causing **6 unwanted mutations to initially correct fields**.
   - For this 4B parameter model without chain-of-thought, single-turn repair prompts were insufficient to recover from structural or grammar failures.

5. **Future Vocabulary Assessment (Q5)**:
   - HESchema's relationship checks function effectively as application-level validator extensions. However, synthetic frequencies from 65 benchmark cases do not represent enterprise demand or justify standardizing new custom JSON Schema vocabularies without production telemetry.

All raw logs, reproducible configs, and evaluation scripts are available in `results/juan-report-v1/`. Let me know if you would like to review the raw ledgers or discuss further!
