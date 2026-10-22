# Proposed Slack Share: Empirical Evaluation of JSON Schema in LLM Structured Output Pipelines

*(Draft ready to share in JSON Schema community channels)*

---

Hey everyone! 👋 

We’ve just completed an extensive empirical evaluation and open-sourced our research and toolkit around using JSON Schema (Draft 2020-12) for LLM structured outputs, schema grammars, and cross-field validation:

**GitHub Repo**: [HarshPopat23/HESchema-](https://github.com/HarshPopat23/HESchema-)  
**Full Technical Report**: [`docs/reports/HESchema_Controlled_Evaluation_Report.md`](file:///d:/20+pro/JHSchema/HESchema-/docs/reports/HESchema_Controlled_Evaluation_Report.md)  
**60-Task Real World Benchmark**: [`docs/reports/HESchema_60_Experiment_Report.md`](file:///d:/20+pro/JHSchema/HESchema-/docs/reports/HESchema_60_Experiment_Report.md)

### Key Empirical Findings:

1. **Native Grammar Decoding vs. Prompt-Only**:
   - **+86 percentage points conformance**: Prompt-only generation achieved 0% strict JSON validity (with models outputting natural language explanations and chain-of-thought preambles), while native grammar enforcement reached **96.9%** validity.
   - **~20x Latency Reduction**: Native decoding reached median latency of **1.24s** (14 output tokens) vs. **24.4s** (460 output tokens) for prompt-only, as grammar enforcement terminates immediately upon completing the structured JSON object.

2. **The "Schema Illusion" & Cross-Field Consistency**:
   - Standard JSON Schema Draft 2020-12 constraints (`const`, `enum`, `minimum`, `maximum`, `required`, `additionalProperties: false`) were 100% enforced natively.
   - However, **18.5% of schema-valid responses passed standard validation despite being factually or logically invalid** (e.g. `total != quantity * unitPrice` or date mismatches). We demonstrate how lightweight contract relationships catch these silent application bugs without requiring heavy new schema keywords.

3. **Provider-Facing Conditional Projection (Honest Negative Result)**:
   - While compiling `if/then/else` conditionals into expanded `oneOf` object branches preserves offline semantic equivalence (verified across 2,200 synthetic instances with 0 mismatches), **live projection did not improve and slightly degraded inference** (-7.75 pp) due to increased GBNF grammar state complexity.

4. **Single-Turn Natural Language Repair (Honest Negative Result)**:
   - Automated single-turn error feedback yielded **0.0% recovery** across Generic, Raw, and Actionable feedback styles on small local models, and even introduced 6 unwanted mutations to initially correct fields.

All reproducible scripts, test packs, and evaluation ledgers are in the repository. We’d love your thoughts, feedback, and discussion!
