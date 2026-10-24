# H60 results correction: independent offline rescoring

The earlier report is superseded. Its membership correctness and false-acceptance headlines used runtime `success` as a task oracle. Membership-only contracts can return accepted with valid relationship checks and `success: false` because no source binding establishes full intent. That was incorrectly labeled an incorrect answer.

These are **offline rescored historical outputs**, not new inference, fresh tasks or proof of production performance. Original raw responses and historical summary remain unchanged. `independent-rescore.json` pins their SHA-256. The checker accepts legitimate alternative answers and does not call HESchema's relationship or calculation evaluator.

| Arm | Slots | First correct | Final correct | Wrong accepted | Correct rejected |
|---|---:|---:|---:|---:|---:|
| A | 540 | 494 | 507 | 27 | 0 |
| B | 540 | 436 | 489 | 0 | 0 |
| C | 540 | 446 | 485 | 0 | 0 |
| D | 540 | 409 | 463 | 0 | 0 |

D correctness refers to system output assembled from validated inputs, not raw model arithmetic. Zero observed wrong acceptance for B/C/D is not a guarantee. Ordinary schema plus conventional application checks can express these task checks; these results do not establish a need for new vocabulary. The independent checker shares the ordinary JSON Schema implementation but implements task semantics separately.

The historical study did not retain original provider receipts or finish reasons and does not establish complete physical-request usage, billed cost or a controlled latency improvement. Its 2,160 rows are 60 tasks × 3 models × 3 repeats × 4 arms, not 2,160 independent tasks. Full/compact prompt trade-offs vary by task and repairs.

The original source snapshot archive referenced by the dataset document is absent from this checkout; the facts were not independently recaptured for this correction. See `research/confirmation-60-v1/RERUN_PROTOCOL.md` for the separately recorded replication and its limitations. Its live progress is not a completed result.

Reproduction: `python scripts/rescore_confirmation60.py --check`; controls: `pytest -q tests/test_confirmation60_oracle.py`.
