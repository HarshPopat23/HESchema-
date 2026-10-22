# Reproducibility Guide: Controlled Evaluation Experiments

This document records the exact environment, dataset hashes, commands, and artifact inventory to reproduce the experimental findings in `docs/reports/HESchema_Controlled_Evaluation_Report.md`.

## 1. Environment & Commit Identity

- **Git Commit**: `3329b864c8bda90807a30d029b1d8d4dc603a5ea`
- **Clean / Dirty**: Clean working tree on branch `main`
- **Dependencies**: `heschema` 0.1.0, `jsonschema` 4.25.1, `httpx` 0.27.0, `fastapi` 0.142.4, `numpy` 2.3.1, `scipy` 1.16.3, Python 3.13.13
- **Local LLM Engine**: Ollama `0.32.0`
- **Model**: `qwen3:4b-instruct` (Digest: `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`)

## 2. Dataset Hashes & Verification

- `controlled_report_cases_65.jsonl`: `cff4f62a73f9085b5cb4150929e27b2f38129de3fdca64fb0bbe53b55ff5f2e9` (65 records)
- `controlled_pilot_cases_13.jsonl`: `c59cfc16a45ca4014c7b8015e2d7f1e491f29a62cee564280447e4c274ee17d5` (13 records)
- `controlled_validator_probes_77.jsonl`: `3774336d29098bd8cdb3e9d2856f36255231323716217c614bf5be1c100a07ba` (77 records)

## 3. Reproduction Commands

### Step A: Preflight Audits
```sh
# Offline fixture and probe verification
python research/controlled-eval-v1/audit_test_pack.py --out results/controlled-report-v1/preflight/offline_audit.json

# 77 probe evaluation and 2,200 candidate differential projection audit
python scripts/evaluate_validator_probes.py
```

### Step B: Exploratory Decoding Study (Stage A)
```sh
# Run 65 cases across 3 modes with 1 repeat (198 requests total)
python -m heschema.cli decoding-study --execute \
  --dataset research/controlled-eval-v1/controlled_report_cases_65.jsonl \
  --provider ollama --model qwen3:4b-instruct \
  --repeats 1 --warmup 3 --max-tokens 1024 --seed 42 --max-requests 198 \
  --out results/controlled-report-v1/exploratory/qwen3_4b_instruct/first
```

### Step C: Replayed Repair Study (Stage B)
```sh
# Replay first-pass outputs across generic, raw, and actionable feedback at budgets 0 and 1
python -m heschema.cli repair-study --execute \
  --dataset research/controlled-eval-v1/controlled_report_cases_65.jsonl \
  --provider ollama --model qwen3:4b-instruct \
  --first-out results/controlled-report-v1/exploratory/qwen3_4b_instruct/first \
  --budgets 0 1 --styles generic raw actionable --max-requests 585 \
  --out results/controlled-report-v1/exploratory/qwen3_4b_instruct/repair
```

### Step D: Statistical Analysis & Summary Generation
```sh
# Generate summary.csv and report_statistics.json
python scripts/analyze_controlled_report.py
```

## 4. Generated Deliverables Inventory

| Path | Purpose |
|:---|:---|
| `docs/reports/HESchema_Controlled_Evaluation_Report.md` | Full narrative report answering Q1–Q5 |
| `results/controlled-report-v1/summary.csv` | Full metric rollup table |
| `results/controlled-report-v1/report_statistics.json` | JSON statistical ledger with bootstrap CIs |
| `results/controlled-report-v1/validator_probe_results.json` | 77 probe offline evaluation records |
| `results/controlled-report-v1/projection_audit.json` | 2,200 candidate instance differential projection audit |
| `results/controlled-report-v1/exploratory/qwen3_4b_instruct/first/runs.jsonl` | Raw Stage A execution logs |
| `results/controlled-report-v1/exploratory/qwen3_4b_instruct/repair/runs.jsonl` | Raw Stage B replayed repair logs |
