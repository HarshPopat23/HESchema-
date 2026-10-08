"""Paired effects, cluster bootstrap, Wilson intervals and exact McNemar tests."""

from collections import defaultdict
from math import sqrt

import numpy as np
from scipy.stats import binomtest


def rate(numerator, denominator):
    return numerator / denominator if denominator else None


def wilson(successes, n):
    if not n:
        return None
    z = 1.959963984540054
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [0.0 if successes == 0 else max(0, centre - half) * 100,
            100.0 if successes == n else min(1, centre + half) * 100]


def paired_effect(rows, baseline, treatment, samples=2000, seed=42):
    paired = defaultdict(dict)
    for row in rows:
        paired[(row["caseId"], row["repeat"])][row["arm"]] = row
    clusters = defaultdict(list)
    wins = losses = 0
    for pair in paired.values():
        if baseline not in pair or treatment not in pair:
            continue
        a, b = pair[baseline], pair[treatment]
        x, y = int(a["firstPassSuccess"]), int(b["firstPassSuccess"])
        clusters[a.get("cluster", a["caseId"])].append((x, y))
        wins += y > x
        losses += x > y
    if not clusters:
        return {"pairedRuns": 0, "absoluteUpliftPoints": None, "relativeImprovementPercent": None,
                "errorReductionPercent": None, "confidenceInterval95": None, "mcnemarExactP": None}
    means = np.array([np.mean(group, axis=0) for group in clusters.values()])
    before, after = means.mean(axis=0)
    rng = np.random.default_rng(seed)
    boot = np.empty(samples)
    for i in range(samples):
        sample = means[rng.integers(0, len(means), len(means))]
        boot[i] = (sample[:, 1] - sample[:, 0]).mean() * 100
    ci = np.quantile(boot, [0.025, 0.975]).tolist()
    # Repeated runs from one prompt are dependent. McNemar is valid only for
    # one paired observation per independent cluster; otherwise suppress p.
    independent = all(len(group) == 1 for group in clusters.values())
    p = float(binomtest(wins, wins + losses, 0.5).pvalue) if independent and wins + losses else (1.0 if independent else None)
    return {"pairedRuns": sum(map(len, clusters.values())), "independentClusters": len(clusters),
            "baselineSuccessPercent": float(before * 100), "treatmentSuccessPercent": float(after * 100),
            "absoluteUpliftPoints": float((after - before) * 100),
            "relativeImprovementPercent": float((after - before) / before * 100) if before else None,
            "errorReductionPercent": float((after - before) / (1 - before) * 100) if before < 1 else None,
            "confidenceInterval95": ci, "mcnemarExactP": p,
            "discordantWins": wins, "discordantLosses": losses,
            "effect": "improvement" if ci[0] > 0 else "harm" if ci[1] < 0 else "inconclusive"}


def summarize(rows):
    n = len(rows)
    first = sum(r["firstPassSuccess"] for r in rows)
    final = sum(r["finalSuccess"] for r in rows)
    available = [r for r in rows if r["status"] == "ok"]
    calls = [r for r in rows if r["expectedAction"] == "call_tool"]
    schema_valid = [r for r in calls if r["firstEvaluation"]["candidateSchemaValid"]
                    and (r["firstEvaluation"].get("parsed") or {}).get("action") == "call_tool"]
    retried = [r for r in rows if r["repairAttempts"] > 0]
    failed_first = [r for r in rows if not r["firstPassSuccess"]]
    latencies = [r["latencyMs"] for r in available]
    costs = [r["costUsd"] for r in rows]
    cost_known = bool(rows) and all(c is not None for c in costs)
    input_known = bool(rows) and all(r["inputTokens"] is not None for r in rows)
    output_known = bool(rows) and all(r["outputTokens"] is not None for r in rows)
    return {"runs": n, "providerErrors": n - len(available),
            "firstPassSuccessPercent": rate(first * 100, n), "finalSuccessPercent": rate(final * 100, n),
            "firstPassWilson95": wilson(first, n),
            "semanticAccuracyPercent": rate(sum(r["firstEvaluation"]["semanticValid"] for r in rows) * 100, n),
            "callSchemaValidityPercent": rate(len(schema_valid) * 100, len(calls)),
            "semanticPrecisionAmongValidCallsPercent": rate(sum(r["firstEvaluation"]["semanticValid"] for r in schema_valid) * 100, len(schema_valid)),
            "retryRatePercent": rate(len(retried) * 100, n),
            "recoveryRatePercent": rate(sum(r["finalSuccess"] for r in failed_first) * 100, len(failed_first)),
            "meanRepairAttempts": rate(sum(r["repairAttempts"] for r in rows), n),
            "transportRetries": sum(r["transportRetries"] for r in rows),
            "inputTokens": sum(r["inputTokens"] for r in rows) if input_known else None,
            "outputTokens": sum(r["outputTokens"] for r in rows) if output_known else None,
            "totalCostUsd": sum(costs) if cost_known else None,
            "costPerSuccessfulTaskUsd": rate(sum(costs), final) if cost_known else None,
            "latencyP50Ms": float(np.quantile(latencies, 0.5)) if latencies else None,
            "latencyP95Ms": float(np.quantile(latencies, 0.95)) if latencies else None,
            "meanValidationMs": rate(sum(r["firstEvaluation"]["validationMs"] for r in rows), n),
            "fitnessPercent": rate(first * 100, n)}


def classify(summary, probes):
    """Descriptive flags, not causal diagnoses. Thresholds are provisional."""
    labels = []
    validity = summary["callSchemaValidityPercent"]
    semantics = summary["semanticPrecisionAmongValidCallsPercent"]
    fps = summary["firstPassSuccessPercent"] or 0
    if validity is not None and semantics is not None:
        if validity >= 95 and semantics >= 90 and fps >= 90:
            labels.append("LLM-friendly")
        elif validity >= 95 and semantics < 85:
            labels.append("high-validity-low-semantic-accuracy")
        elif validity < 85:
            labels.append("low-validity; inspect errors before diagnosing complexity")
    if (probes.get("falseRejectionPercent") or 0) > 0:
        labels.append("over-constrained-on-probes")
    if (probes.get("invalidRejectionPercent") or 0) < 80:
        labels.append("under-constrained-on-probes")
    if fps < 85 and (summary["finalSuccessPercent"] or 0) >= 95 and (summary["retryRatePercent"] or 0) >= 15:
        labels.append("retry-dependent")
    return labels or ["needs-more-evidence"]


def custom_fitness(summary, probes, model_stability=None):
    """User-proposed weights, not a calibrated probability or industry standard."""
    spv = summary["semanticPrecisionAmongValidCallsPercent"]
    irr = probes.get("invalidRejectionPercent")
    if spv is None or irr is None or model_stability is None:
        return None
    return (0.45 * summary["firstPassSuccessPercent"] + 0.20 * spv + 0.15 * irr
            + 0.10 * (100 - summary["retryRatePercent"]) + 0.10 * model_stability)


def compare_models(reports):
    """Cross-model gap is descriptive; callers must specify small/large ordering."""
    if len(reports) < 2:
        raise ValueError("Supply small-model report first and large-model report second")
    a, b = reports[0], reports[1]
    if any(not r["complete"] for r in reports):
        raise ValueError("Complete both model experiments before comparison")
    if any(not r.get("comparisonValid") for r in reports):
        raise ValueError("Model comparison requires real, error-free, fixed-model experiments")
    for key in ("datasetHash", "schemaHashes", "minimalSchemaHashes", "repeats", "repairs", "seed", "maxTokens", "temperature", "decodingMode"):
        if a["config"][key] != b["config"][key]:
            raise ValueError(f"Reports have different {key}")
    small, large = a["arms"]["input_schema"], b["arms"]["input_schema"]
    gap = large["firstPassSuccessPercent"] - small["firstPassSuccessPercent"]
    stability = 100 - abs(gap)
    return {"modelGapPoints": gap, "modelStabilityPercent": stability,
            "modelSensitive": gap >= 15,
            "customFitnessSmall": custom_fitness(small, a["probes"], stability),
            "customFitnessLarge": custom_fitness(large, b["probes"], stability)}
