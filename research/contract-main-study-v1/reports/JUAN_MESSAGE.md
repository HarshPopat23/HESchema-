# Update for Juan: HESchema Controlled Evaluation Results

Hi Juan,

We have completed the controlled benchmark comparing ordinary JSON Schema (Arm A) against HESchema contracts with approved context (Arm B) across the frozen 100-input study pack.

### Key Measured Outcomes:
- **First-Pass Correctness:** Arm A achieved **89.78%**, while Arm B achieved **87.44%** (-2.34% delta).
- **Final Correctness (with 1 repair):** Arm A reached **91.22%**, while Arm B reached **88.33%** (-2.89% delta).
- **False Acceptance Reduction:** Arm A accepted invalid outputs **6.89%** of the time (blind to arithmetic and cross-field mismatches). Arm B reduced false acceptances to **0.0%**.
- **Overhead:** Arm B introduced a **+48.0% token overhead** and an average latency difference of **430.0 ms**.

### Full Reports & Artifacts:
- Main Scientific Report: `research/contract-main-study-v1/reports/MAIN_REPORT.md`
- Non-Technical Summary: `research/contract-main-study-v1/reports/EXECUTIVE_SUMMARY.md`
- Evidence Boundaries: `research/contract-main-study-v1/reports/LIMITATIONS.md`
- Raw Execution Logs: `research/contract-main-study-v1/runs/`

Please let me know if you would like to review the paired case breakdowns or examine specific failure modes.
