"""Reproducible analysis script for HESchema Controlled Evaluation Report.
Processes first-pass decoding and repair runs to build summary.csv, contrast tables, and statistical summaries.
"""

import argparse
import csv
import json
import os
import random
from collections import defaultdict
from pathlib import Path

import numpy as np


def load_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def calculate_stats(values):
    if not values:
        return {"count": 0, "mean": None, "median": None, "p90": None}
    arr = np.array(values)
    return {
        "count": len(arr),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "p90": float(np.percentile(arr, 90))
    }

def bootstrap_diff(a_vals, b_vals, clusters, n_boot=10000, seed=42):
    """Cluster bootstrap by family for paired differences."""
    rng = random.Random(seed)
    unique_clusters = list(set(clusters))
    diffs = []
    
    # Pre-organize by cluster
    by_cluster = defaultdict(list)
    for a, b, c in zip(a_vals, b_vals, clusters):
        by_cluster[c].append((a, b))
        
    for _ in range(n_boot):
        sample_clusters = rng.choices(unique_clusters, k=len(unique_clusters))
        boot_a, boot_b = [], []
        for sc in sample_clusters:
            for a, b in by_cluster[sc]:
                boot_a.append(a)
                boot_b.append(b)
        diffs.append(np.mean(boot_b) - np.mean(boot_a))
        
    arr = np.array(diffs)
    return {
        "mean_diff": float(np.mean(arr)),
        "ci_lower": float(np.percentile(arr, 2.5)),
        "ci_upper": float(np.percentile(arr, 97.5))
    }

def analyze(first_dir, repair_dir, out_csv_path, report_stats_path=None):
    first_runs = load_jsonl(Path(first_dir) / "runs.jsonl")
    first_config = json.loads((Path(first_dir) / "config.json").read_text(encoding="utf-8")) if os.path.exists(Path(first_dir) / "config.json") else {}
    
    repair_runs = load_jsonl(Path(repair_dir) / "runs.jsonl") if repair_dir and os.path.exists(Path(repair_dir) / "runs.jsonl") else []
    
    model = first_config.get("requestedModel", "qwen3:4b-instruct")
    
    # 1. Summary CSV Generation
    csv_rows = []
    
    # Group first pass by mode and family
    first_groups = defaultdict(list)
    for r in first_runs:
        mode = r["arm"]
        family = r.get("cluster", "unknown")
        first_groups[(model, mode, family, "none", 0)].append(r)
        
    # Group repair runs by mode, family, style, budget
    repair_groups = defaultdict(list)
    for r in repair_runs:
        # caseId format: J001:prompt_only
        case_parts = r["caseId"].split(":")
        source_mode = case_parts[1] if len(case_parts) > 1 else "unknown"
        family = r.get("cluster", "unknown")
        arm_parts = r["arm"].split(":")
        style = arm_parts[0] if len(arm_parts) > 1 else r["arm"]
        budget = int(arm_parts[1]) if len(arm_parts) > 1 else 0
        repair_groups[(model, source_mode, family, style, budget)].append(r)
        
    all_groups = {}
    for k, v in first_groups.items():
        all_groups[k] = {"type": "first", "rows": v}
    for k, v in repair_groups.items():
        all_groups[k] = {"type": "repair", "rows": v}
        
    for (m, mode, fam, style, b), ginfo in all_groups.items():
        rows = ginfo["rows"]
        n = len(rows)
        if ginfo["type"] == "first":
            accepted = sum(1 for r in rows if r["status"] == "ok")
            rejected = sum(1 for r in rows if r["status"] == "native_request_rejected")
            json_valid = sum(1 for r in rows if r["firstEvaluation"]["stages"]["json"] == "valid")
            orig_valid = sum(1 for r in rows if r["firstEvaluation"]["stages"]["originalSchema"] == "valid")
            eff_valid = sum(1 for r in rows if r["firstEvaluation"]["stages"]["context"] == "valid")
            rel_valid = sum(1 for r in rows if r["firstEvaluation"]["stages"]["relationships"] == "valid")
            success = sum(1 for r in rows if r["firstPassSuccess"])
            agreement = sum(1 for r in rows if r["firstEvaluation"]["intentAgreement"] is True)
            
            latencies = [r["latencyMs"] for r in rows if r.get("latencyMs")]
            in_toks = [r["attempts"][0]["generation"]["input_tokens"] for r in rows if r["attempts"] and r["attempts"][0]["generation"].get("input_tokens") is not None]
            out_toks = [r["attempts"][0]["generation"]["output_tokens"] for r in rows if r["attempts"] and r["attempts"][0]["generation"].get("output_tokens") is not None]
            new_requests = sum(r.get("requestsAttempted", 1) for r in rows)
        else:
            accepted = sum(1 for r in rows if r.get("status") == "ok")
            rejected = 0
            json_valid = sum(1 for r in rows if (r.get("finalEvaluation") or {}).get("stages", {}).get("json") == "valid")
            orig_valid = sum(1 for r in rows if (r.get("finalEvaluation") or {}).get("stages", {}).get("originalSchema") == "valid")
            eff_valid = sum(1 for r in rows if (r.get("finalEvaluation") or {}).get("stages", {}).get("context") == "valid")
            rel_valid = sum(1 for r in rows if (r.get("finalEvaluation") or {}).get("stages", {}).get("relationships") == "valid")
            success = sum(1 for r in rows if r.get("finalSuccess"))
            agreement = sum(1 for r in rows if (r.get("finalEvaluation") or {}).get("intentAgreement") is True)
            
            latencies = [r["latencyMs"] for r in rows if r.get("latencyMs")]
            in_toks = [r["attempts"][-1]["generation"]["input_tokens"] for r in rows if r.get("attempts") and r["attempts"][-1].get("generation", {}).get("input_tokens") is not None]
            out_toks = [r["attempts"][-1]["generation"]["output_tokens"] for r in rows if r.get("attempts") and r["attempts"][-1].get("generation", {}).get("output_tokens") is not None]
            new_requests = sum(r.get("requestsAttempted", 0) for r in rows)

        l_stats = calculate_stats(latencies)
        in_stats = calculate_stats(in_toks)
        out_stats = calculate_stats(out_toks)
        
        csv_rows.append({
            "model": m,
            "mode": mode,
            "family": fam,
            "style": style,
            "budget": b,
            "attempts": n,
            "accepted": accepted,
            "accepted_pct": round(accepted / n * 100, 2) if n else 0,
            "native_rejected": rejected,
            "json_valid": json_valid,
            "json_valid_pct": round(json_valid / n * 100, 2) if n else 0,
            "original_schema_valid": orig_valid,
            "original_schema_valid_pct": round(orig_valid / n * 100, 2) if n else 0,
            "context_valid": eff_valid,
            "relationships_valid": rel_valid,
            "task_agreement": agreement,
            "task_agreement_pct": round(agreement / n * 100, 2) if n else 0,
            "overall_success": success,
            "overall_success_pct": round(success / n * 100, 2) if n else 0,
            "requests_made": new_requests,
            "median_latency_ms": round(l_stats["median"], 1) if l_stats["median"] else None,
            "p90_latency_ms": round(l_stats["p90"], 1) if l_stats["p90"] else None,
            "mean_out_tokens": round(out_stats["mean"], 1) if out_stats["mean"] else None,
            "mean_in_tokens": round(in_stats["mean"], 1) if in_stats["mean"] else None
        })
        
    # Write CSV
    if csv_rows:
        headers = list(csv_rows[0].keys())
        with open(out_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(csv_rows)
        print(f"Saved {out_csv_path} with {len(csv_rows)} rows.")
        
    return csv_rows

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--first", default="results/controlled-report-v1/exploratory/qwen3_4b_instruct/first")
    parser.add_argument("--repair", default="results/controlled-report-v1/exploratory/qwen3_4b_instruct/repair")
    parser.add_argument("--out-csv", default="results/controlled-report-v1/summary.csv")
    args = parser.parse_args()
    analyze(args.first, args.repair, args.out_csv)
