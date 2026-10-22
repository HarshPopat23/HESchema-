# HESchema Controlled Evaluation Benchmark Suite

This directory contains the controlled evaluation suite, test fixtures, offline probes, and reproducibility guidelines for evaluating JSON Schema constraints in LLM structured output pipelines.

| File | Purpose |
| --- | --- |
| `controlled_report_cases_65.jsonl` | Main inputs: 65 cases, 13 families, five cases each |
| `controlled_pilot_cases_13.jsonl` | Feasibility subset: one case per family |
| `controlled_validator_probes_77.jsonl` | 65 known negative outputs plus 12 JSON, context and control checks |
| `ANTIGRAVITY_PROMPT.md` | Detailed evaluation/report task specification |
| `CASE_INDEX.md` | Human-readable list of all 65 main prompts |
| `audit_test_pack.py` | Offline fixture, counterexample and oracle-separation audit |
| `offline_audit.json` | Passed audit verification |
| `manifest.json` | Dataset versions, hashes, counts, provenance and request ceilings |

The 13 families cover source interpretation, product/sum/date/identifier relationships, approved const values, trusted enum sets and numeric bounds, finite conditionals, uniqueness, overlapping oneOf, local references and runtime reference membership.

These inputs are synthetic evaluation cases for controlled reproducibility. The offline audit verified the positive oracles and intended probe outcomes.

Run:
```sh
python audit_test_pack.py --out local_offline_audit.json
heschema decoding-study --dataset controlled_report_cases_65.jsonl --repeats 3 --warmup 3
```
