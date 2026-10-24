> **Raw-evidence publication pending:** automatic approval review requires explicit authorization for four raw-response archives. They were verified locally but are not in this PR; independent replay from the PR alone is currently blocked. See `rerun-20261024/PUBLICATION_STATUS.md`.

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

## New replication (24 October 2026)

All 2,160 selected slots have matched response/usage receipts after explicitly recorded reconciliation. Three derived rows were recovered from intact receipts. Two original slots lacked complete initial receipts and were replaced; their entire matched group is excluded from the primary comparison: **539 trials per arm, 2,156 primary slots**. Original artifacts remain archived. The cause of the missing writes is unknown.

| Arm | Primary slots | First correct | Final correct | Wrong accepted | Correct rejected |
|---|---:|---:|---:|---:|---:|
| A | 539 | 482 | 486 | 49 | 0 |
| B | 539 | 450 | 488 | 0 | 0 |
| C | 539 | 439 | 484 | 0 | 0 |
| D | 539 | 423 | 477 | 0 | 0 |

COMPACT used **19.53% fewer total primary tokens than FULL**, including repair usage. Its slightly lower observed correctness is not proof of non-inferiority. The FULL-versus-ordinary final-correctness interval includes zero. Conventional application checks also caught all observed wrong primary outputs in offline replay; this is not proof that new JSON Schema vocabulary is necessary.

D did not improve aggregate correctness: sums/products matched COMPACT, but counts regressed. Keep application calculation optional. Zero observed wrong acceptance does not establish a universal guarantee. No controlled latency improvement or billed-cost saving is claimed.

Full report: `research/confirmation-60-v1/rerun-20261024/REPORT.md`. Stratified metrics, physical request states and descriptive project-bootstrap intervals: `verified-summary.json`. Raw returned contents/usage and failed or unverifiable requests: `request-evidence.jsonl.gz`. Reconciliation and original artifacts are preserved alongside them.
