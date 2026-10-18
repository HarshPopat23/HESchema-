# HESchema Main Study: Input Validation Report

**Verification Date:** 2026-10-18
**Study Pack Commit:** `c405078eb59aa5179ff004ce7efced4f37b34f8b`
**Input File:** `research/HESchema_Main_Study_100_Inputs.md`

## 1. Hash & Provenance Verification

| Check | Expected | Actual | Status |
|---|---|---|---|
| Study Markdown SHA-256 | `f140699197d823a39ffbd614499ff5b8c628f6fb64d9a306aaa1ce8e89eb15e2` | `f140699197d823a39ffbd614499ff5b8c628f6fb64d9a306aaa1ce8e89eb15e2` | **PASS** |
| Ordered 100-Case Array SHA-256 | `ab558fabd054f061fe2cc2425f84ea51c6b1fd1043a943697a8f06c4514cec05` | `ab558fabd054f061fe2cc2425f84ea51c6b1fd1043a943697a8f06c4514cec05` | **PASS** |
| Source Archive SHA-256 | `85c45d2c44258f6e1fe46cb22440395cadee5a0ccb3031547886e83c9111a408` | `85c45d2c44258f6e1fe46cb22440395cadee5a0ccb3031547886e83c9111a408` | **PASS** |
| Extracted Cases Count | 100 | 100 | **PASS** |
| Unique Case IDs | 100 | 100 | **PASS** |
| Restored Source Files | 152 | 152 | **PASS** |

## 2. Ecosystem Case Distribution

| Ecosystem Prefix | Source System | Target Cases | Extracted Cases | Status |
|---|---|---:|---:|---|
| `WF` | WfCommons WfInstances | 20 | 20 | **PASS** |
| `USGS` | USGS Earthquake API | 20 | 20 | **PASS** |
| `GBFS` | Citi Bike Discovery Feed (GBFS 1.1) | 20 | 20 | **PASS** |
| `CR` | Crossref REST API | 20 | 20 | **PASS** |
| `PYPI` | PyPI JSON API | 20 | 20 | **PASS** |

## 3. Schema & Relationship Positive Checks

| Verification Target | Expected | Passing | Status |
|---|---:|---:|---|
| Ordinary Schema Validation on Expected Output | 100 | 100 | **PASS** |
| Context Effective Schema on Expected Output | 100 | 100 | **PASS** |
| Missing Context Bindings | 0 | 0 | **PASS** |
| Declared Relationships on Reference Output | 192 | 192 | **PASS** |
| Total Active Context Bindings | 412 | 412 | **PASS** |

## 4. Isolation Guarantee

- `evaluation/gold.private.jsonl` contains reference outputs strictly reserved for the evaluator.
- `inputs/model_inputs.jsonl` contains solely `id`, `prompt`, `contract`, and `context`.
- Neither `expected_output`, `expected_output_origin`, nor `source_field_map` will enter generation or repair prompts.
