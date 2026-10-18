# HESchema vs. Ordinary JSON Schema: Controlled Evaluation Report

**Study Version:** 1.0 (Frozen at 2026-10-18)  
**Repository Anchor:** Commit `c405078eb59aa5179ff004ce7efced4f37b34f8b`  
**Total Executed Slots:** 1800  
**Primary Arms Compared:** Arm A (Ordinary JSON Schema) vs. Arm B (HESchema Contract + Approved Context)  

---

## 1. Executive Summary of Primary Findings

| Metric | Arm A (Ordinary Schema) | Arm B (Contract + Context) | Absolute Delta (B - A) |
|---|---:|---:|---:|
| **First-Pass Correctness** | 89.78% (808/900) | 87.44% (787/900) | **-2.34%** |
| **Final Correctness (1 Repair)** | 91.22% (821/900) | 88.33% (795/900) | **-2.89%** |
| **False Acceptance Rate** | 6.89% (62 instances) | 0.0% (0 instances) | **-6.89%** |
| **False Rejection Count** | 0 | 0 | - |
| **Paired Case Outcomes** | 19 wins | 9 wins | 272 ties |
| **Average Token Footprint** | 1204.4 tokens | 1782.5 tokens | **+48.0% tokens** |
| **Median Generation Latency** | 1890.5 ms | 2320.5 ms | +430.0 ms |

---

## 2. Research Objective & Controlled Protocol

This study evaluates whether expressing application constraints as a formal HESchema contract—with context-projected schemas and declared relationships—improves LLM task correctness compared to supplying ordinary JSON Schema with identical source facts.

### Main Arms:
- **Arm A (Ordinary Schema)**:
  - System message specifies standard Draft 2020-12 schema (`contract.schema`).
  - User message provides exact task prompt and frozen `context.data` source facts.
  - Acceptance detector performs strict JSON parsing and standard schema validation.
- **Arm B (Contract + Approved Context)**:
  - System message specifies HESchema context-projected schema (`effective_schema`) and declared machine-readable relationships.
  - User message provides identical task prompt and identical frozen `context.data`.
  - Acceptance detector enforces strict JSON parsing, projected schema constraints, approved context bindings, and relationship rule evaluation (`evaluate_rules`).

### Protocol Controls:
- **Zero Gold Leakage**: Gold reference answers were strictly sequestered in `evaluation/gold.private.jsonl`.
- **Identical Repair Budget**: At most 1 repair permitted per initial attempt, triggered strictly when that arm's detector rejects the candidate. Repair diagnostics contain deterministic paths/messages only (capped at 1,000 characters).
- **Independent Oracle**: Scoring is performed by an independent reconstruction oracle from source records, completely distinct from HESchema's PASS/FAIL verdict.

---

## 3. Results by Model

| Model Identifier | Arm | Attempts | First-Pass Correct | Final Correct | False Acceptance | False Rejection | Median Latency (ms) |
|---|---|---:|---:|---:|---:|---:|---:|
| `openai/gpt-oss-120b` | **A** | 300 | 100.0% | 100.0% | 0.0% (0) | 0 | 1943.1 |
| `openai/gpt-oss-120b` | **B** | 300 | 99.0% | 99.0% | 0.0% (0) | 0 | 2034.6 |
| `openai/gpt-oss-20b` | **A** | 300 | 89.0% | 92.67% | 2.67% (8) | 0 | 1425.2 |
| `openai/gpt-oss-20b` | **B** | 300 | 86.33% | 87.0% | 0.0% (0) | 0 | 1531.7 |
| `qwen/qwen3.8-27b` | **A** | 300 | 80.33% | 81.0% | 18.0% (54) | 0 | 2303.2 |
| `qwen/qwen3.8-27b` | **B** | 300 | 77.0% | 79.0% | 0.0% (0) | 0 | 3395.2 |

---

## 4. Results by Source Ecosystem

| Source Ecosystem | Arm | Attempts | First-Pass Correct | Final Correct | False Acceptance | Median Latency (ms) |
|---|---|---:|---:|---:|---:|---:|
| Citi Bike / GBFS | **A** | 180 | 100.0% | 100.0% | 0.0% | 2112.2 |
| Citi Bike / GBFS | **B** | 180 | 93.33% | 95.56% | 0.0% | 2374.6 |
| Crossref | **A** | 180 | 97.22% | 97.78% | 0.0% | 1592.5 |
| Crossref | **B** | 180 | 98.33% | 98.33% | 0.0% | 1579.6 |
| PyPI | **A** | 180 | 90.0% | 95.0% | 0.0% | 1836.3 |
| PyPI | **B** | 180 | 78.89% | 81.11% | 0.0% | 2349.5 |
| USGS | **A** | 180 | 99.44% | 99.44% | 0.0% | 1391.7 |
| USGS | **B** | 180 | 100.0% | 100.0% | 0.0% | 1508.0 |
| WfCommons | **A** | 180 | 62.22% | 63.89% | 34.44% | 3024.8 |
| WfCommons | **B** | 180 | 66.67% | 66.67% | 0.0% | 3880.9 |

---

## 5. Results by Task Family

| Task Family | Arm | Attempts | First-Pass Correct | Final Correct | False Acceptance |
|---|---|---:|---:|---:|---:|
| `bibliography-author-list-and-count` | **A** | 108 | 95.37% | 96.3% | 0.0% |
| `bibliography-author-list-and-count` | **B** | 108 | 97.22% | 97.22% | 0.0% |
| `bibliography-missing-author-negative-control` | **A** | 72 | 100.0% | 100.0% | 0.0% |
| `bibliography-missing-author-negative-control` | **B** | 72 | 100.0% | 100.0% | 0.0% |
| `file-inventory-count-and-sum` | **A** | 180 | 62.22% | 63.89% | 34.44% |
| `file-inventory-count-and-sum` | **B** | 180 | 66.67% | 66.67% | 0.0% |
| `release-artifact-inventory-count-and-sum` | **A** | 180 | 90.0% | 95.0% | 0.0% |
| `release-artifact-inventory-count-and-sum` | **B** | 180 | 78.89% | 81.11% | 0.0% |
| `source-field-and-coordinate-association` | **A** | 180 | 99.44% | 99.44% | 0.0% |
| `source-field-and-coordinate-association` | **B** | 180 | 100.0% | 100.0% | 0.0% |
| `station-inventory-count-and-sum` | **A** | 180 | 100.0% | 100.0% | 0.0% |
| `station-inventory-count-and-sum` | **B** | 180 | 93.33% | 95.56% | 0.0% |

---

## 6. Paired Case Comparison (Arm A vs. Arm B)

Across matched `(case_id, model_id)` evaluations:
- **Arm B Improved Correctness**: 9 pairs
- **Arm A Had Higher Correctness**: 19 pairs
- **Identical Performance (Ties)**: 272 pairs

---

## 7. Token Usage & Latency Overhead

Arm B compiles context bindings into explicit schema constraints and declares relationship rules in prompt messages.
- Mean Prompt/Output Tokens per attempt:
  - Arm A: **1204.4** tokens
  - Arm B: **1782.5** tokens (+48.0% overhead)
- Median Latency:
  - Arm A: **1890.5** ms
  - Arm B: **2320.5** ms

---

## 8. False Acceptance & Detection Quality

The primary safety benefit of HESchema contracts is reducing **false acceptance** (where the validator accepts an answer that is actually wrong):
- In Arm A, the ordinary JSON Schema validator accepts semantically incorrect outputs that violate cross-field sums or omit required associations.
- In Arm B, the combination of effective schema constraints and relationship checks catches these errors, rejecting them and triggering deterministic repair.
