# HESchema testing package for Juan's research proposal

Start by giving Antigravity `ANTIGRAVITY_PROMPT.md` and this entire directory. The prompt names the current HESchema interfaces and includes exact experiment commands, budgets, scoring rules and report deliverables.

| File | Purpose |
| --- | --- |
| `juan_report_cases_65.jsonl` | Main inputs: 65 cases, 13 families, five cases each |
| `juan_pilot_cases_13.jsonl` | Feasibility subset: one case per family |
| `juan_validator_probes_77.jsonl` | 65 known negative outputs plus 12 JSON, context and control checks |
| `ANTIGRAVITY_PROMPT.md` | Detailed evaluation/report task to paste into Antigravity |
| `CASE_INDEX.md` | Human-readable list of all 65 main prompts |
| `audit_test_pack.py` | Offline fixture, counterexample and oracle-separation audit |
| `offline_audit.json` | Passed audit against HESchema commit `a044e3911fc84c0a4b2684797566b7c370fce40c` |
| `manifest.json` | Dataset versions, hashes, counts, provenance and request ceilings |

The 13 families cover source interpretation, product/sum/date/identifier relationships, approved const values, trusted enum sets and numeric bounds, finite conditionals, uniqueness, overlapping oneOf, local references and runtime reference membership.

These inputs are assistant-created synthetic evaluation cases, awaiting independent human review. They are not company reports, adoption evidence, a keyword-support proof or live inference results. The offline audit verified the positive oracles and intended probe outcomes. Its projection checks are finite examples, not a general equivalence proof.

Install the HESchema implementation containing the controlled studies, then run:

```sh
python audit_test_pack.py --out local_offline_audit.json
heschema decoding-study --dataset juan_report_cases_65.jsonl --repeats 3 --warmup 3
```

The second command is a dry run. Real inference requires `--execute`, an available backend/model and explicit request limits. Read the complete Antigravity prompt before running it.

The main design uses three decoding modes and three repeats: 585 measured first passes plus three warmups per model. Repair studies replay the same first outputs with generic/raw/actionable feedback and budgets of 0/1/2, with an upper bound of 5,265 new repair calls per model. Full two-model ceiling: 11,706 requests. The pilot is separate and excluded from that main ceiling.

Scoring oracles (`expected`) must never become generation messages, runtime context or repair feedback. Trusted approved values and totals computed from declared relationships are allowed evidence. In particular, source-wrong outputs that satisfy the contract cannot receive a hidden oracle-informed repair.

There are no empirical model results in this package. Antigravity must run the available real models and preserve all failures, rejections, truncations and uncertainty before producing the new report.
