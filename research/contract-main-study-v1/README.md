# HESchema Main Study: Controlled Evaluation Workspace

This workspace houses the implementation, validation, execution artifacts, and analysis reports for the controlled comparison between ordinary JSON Schema and HESchema contracts with approved context.

---

## Workspace Structure

- `protocol.md`: Locked scientific protocol and experimental constraints.
- `input_validation_report.md`: Verification report for all 100 cases, source archive, and schema checks.
- `run_manifest.json`: Immutable execution manifest capturing commit, hashes, settings, and pricing.
- `inputs/`:
  - `cases.json`: Full 100 benchmark cases.
  - `model_inputs.jsonl`: Isolated input payload sent to models (no reference answers).
- `evaluation/`:
  - `gold.private.jsonl`: Evaluator-side reference answers.
- `sources/`: Restored frozen source files (152 files) verified against `MANIFEST.json`.
- `runner/`:
  - `main_study_runner.py`: Resumable execution adapter with dual key rotation.
  - `oracle.py`: Independent deterministic reconstruction oracle.
  - `strict_parser.py`: Strict JSON validation (no Markdown, no duplicate keys).
  - `detector.py`: Arm-specific acceptance detector policy.
  - `prompt_builder.py`: Prompt and repair message generation.
  - `failure_classifier.py`: Multi-label failure classification engine.
  - `analyze_study.py`: Metrics calculation and report generator.
- `tests/`: Automated unit test suite (`test_study_components.py`).
- `runs/`: Append-only transaction ledgers (`requests.jsonl`, `responses.jsonl`, `attempts.jsonl`, `checkpoints.json`).
- `analysis/`: Generated CSV metrics by model, source, family, and paired comparisons.
- `reports/`:
  - `MAIN_REPORT.md`: Comprehensive academic-grade report.
  - `EXECUTIVE_SUMMARY.md`: 8th-grade reading level plain language summary.
  - `LIMITATIONS.md`: Evidence boundaries and non-claims.
  - `STUDY_STATUS_SUMMARY.md`: Concise executive summary of results.

---

## How to Reproduce

### 1. Run Offline Component Tests
```bash
pytest research/contract-main-study-v1/tests/test_study_components.py
```

### 2. Verify Extraction & Pre-Flight Checks
```bash
python research/contract-main-study-v1/runner/extract_and_validate.py
```

### 3. Execute Experiment Run
To run live experiment against configured models:
```bash
python research/contract-main-study-v1/runner/main_study_runner.py \
  --models "openai/gpt-oss-20b,openai/gpt-oss-120b,qwen/qwen3.8-27b" \
  --repeats 3 \
  --arms "A,B" \
  --run-id run-main-ab
```

### 4. Generate Analysis & Reports
```bash
python research/contract-main-study-v1/runner/analyze_study.py research/contract-main-study-v1/runs/run-main-ab
```
