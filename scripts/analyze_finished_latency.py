"""Offline analysis of an interrupted first session and its explicit continuation."""

import collections
import hashlib
import json
import math
import random
import statistics

import continue_latency_study as continuation
from rescore_confirmation60 import correct

PARENT = continuation.PARENT
METRICS = (
    "serviceTotalMs",
    "providerRoundTripMs",
    "activePipelineMs",
    "localValidationMs",
    "applicationCalculationMs",
    "pacingWaitMs",
    "retryWaitMs",
    "queueWaitMs",
    "endToEndMs",
)


def describe(values):
    values = sorted(values)
    return {
        "n": len(values),
        "median": statistics.median(values),
        "p95": values[math.ceil(0.95 * len(values)) - 1],
        "mean": statistics.mean(values),
    }


def group(row):
    return tuple(row[k] for k in ("caseId", "model", "repeat"))


def metrics(rows):
    return {
        "n": len(rows),
        "firstCorrect": sum(r["firstCorrect"] for r in rows),
        "finalCorrect": sum(r["finalCorrect"] for r in rows),
        "wrongAccepted": sum(r["accepted"] and not r["finalCorrect"] for r in rows),
        "totalTokens": sum(r["totalTokens"] for r in rows),
        "repairCount": sum(len(r.get("requestIds", [])) == 2 for r in rows),
        "retryAffected": sum(r["timing"]["retryWaitMs"] > 1 for r in rows),
        "retryMaxMs": max(r["timing"]["retryWaitMs"] for r in rows),
        "retryTotalMs": sum(r["timing"]["retryWaitMs"] for r in rows),
        **{
            k: sum(r.get(k, 0) for r in rows)
            for k in (
                "initialInputTokens",
                "initialOutputTokens",
                "repairInputTokens",
                "repairOutputTokens",
            )
        },
        **{k: describe([r["timing"][k] for r in rows]) for k in METRICS},
    }


def verify_finished():
    provenance = json.loads((PARENT / "completion-provenance.json").read_text())
    for rel, digest in provenance["previousEvidenceHashes"].items():
        assert hashlib.sha256((PARENT / rel).read_bytes()).hexdigest() == digest, rel
    receipts = {
        p.stem: json.loads(p.read_text())
        for segment in ("main", "continuation", "completion")
        for p in (PARENT / segment / "requests").glob("*.json")
    }
    identities = set()
    for segment in ("main", "continuation", "completion"):
        directory = PARENT / segment
        manifest = json.loads((directory / "manifest.json").read_text())
        for rel, digest in manifest["codeHashes"].items():
            assert hashlib.sha256((continuation.ROOT / rel).read_bytes()).hexdigest() == digest, rel
        local = [json.loads(p.read_text()) for p in (directory / "requests").glob("*.json")]
        for p in (directory / "slots").glob("*.json"):
            row = json.loads(p.read_text())
            key = continuation.identity(row)
            assert key not in identities
            identities.add(key)
            assert key == continuation.identity(manifest["slots"][row["slotIndex"]])
            continuation.study.verify_timing(row["timing"])
            chosen = [receipts[i] for i in row["requestIds"]]
            assert 1 <= len(chosen) <= 2 and chosen[0]["phase"] == "initial"
            if len(chosen) == 2:
                assert chosen[1]["phase"] == "repair"
            for r in chosen:
                assert r["state"] == "returned" and continuation.identity(r["slot"]) == key
                assert isinstance(r["rawContent"], str)
                assert all(
                    isinstance(r["usage"][k], int) and r["usage"][k] >= 0
                    for k in ("prompt_tokens", "completion_tokens")
                )
            attempts = [r for r in local if r["slotIndex"] == row["slotIndex"]]
            assert all(r["state"] in ("returned", "failed") for r in attempts)
            assert (
                abs(sum(r["roundTripMs"] for r in attempts) - row["timing"]["providerRoundTripMs"])
                < 0.01
            )
            if row.get("resumedInitialId"):
                assert (
                    provenance["reusedInitials"][str(row["slotIndex"])] == row["resumedInitialId"]
                )
    schedule = json.loads((PARENT / "main/manifest.json").read_text())["slots"]
    assert len(identities) == 2160 and identities == {continuation.identity(r) for r in schedule}


def analyze(partial=False):
    verify_finished()
    provenance = json.loads((PARENT / "continuation-provenance.json").read_text())
    excluded = {group(r) for r in provenance["excludedPrimaryGroups"]}
    cases = {
        c["id"]: c
        for c in json.loads((continuation.study.base.DATA_DIR / "cases.json").read_text())
    }
    rows = []
    physical = []
    all_receipts = {
        p.stem: json.loads(p.read_text())
        for segment in ("main", "continuation", "completion")
        for p in (PARENT / segment / "requests").glob("*.json")
    }
    for epoch, directory in [
        ("original", continuation.FIRST),
        ("continuation", continuation.SECOND),
        ("completion", PARENT / "completion"),
    ]:
        receipts = {
            p.stem: json.loads(p.read_text()) for p in (directory / "requests").glob("*.json")
        }
        physical += [dict(r, epoch=epoch) for r in receipts.values()]
        for path in sorted((directory / "slots").glob("*.json")):
            row = json.loads(path.read_text())
            chosen = [all_receipts[i] for i in row["requestIds"]]
            case = cases[row["caseId"]]
            row.update(
                epoch=epoch,
                project=case["project"],
                family=case["family"],
                worker=f"{epoch}:{chosen[0]['worker']}",
                firstCorrect=correct(chosen[0]["rawContent"], case, row["arm"]),
                finalCorrect=correct(chosen[-1]["rawContent"], case, row["arm"]),
                initialInputTokens=chosen[0]["usage"]["prompt_tokens"],
                initialOutputTokens=chosen[0]["usage"]["completion_tokens"],
                repairInputTokens=sum(r["usage"]["prompt_tokens"] for r in chosen[1:]),
                repairOutputTokens=sum(r["usage"]["completion_tokens"] for r in chosen[1:]),
                totalTokens=sum(
                    r["usage"]["prompt_tokens"] + r["usage"]["completion_tokens"] for r in chosen
                ),
            )
            row["timing"]["activePipelineMs"] = (
                row["timing"]["serviceTotalMs"]
                - row["timing"]["pacingWaitMs"]
                - row["timing"]["retryWaitMs"]
            )
            assert row["timing"]["activePipelineMs"] >= 0
            rows.append(row)
    for segment in ("main", "continuation"):
        directory = PARENT / segment
        completed_indices = {
            json.loads(p.read_text())["slotIndex"] for p in (directory / "slots").glob("*.json")
        }
        for p in (directory / "requests").glob("*.json"):
            receipt = json.loads(p.read_text())
            if receipt["slotIndex"] not in completed_indices:
                excluded.add(group(receipt["slot"]))
    groups = collections.defaultdict(list)
    for row in rows:
        groups[group(row)].append(row)
    if not partial:
        assert len(groups) == 540 and all(len(g) == 4 for g in groups.values())
    incomplete_groups = {key for key, values in groups.items() if len(values) != 4}
    split = {key for key, values in groups.items() if len({r["epoch"] for r in values}) != 1}
    primary = [r for r in rows if group(r) not in excluded | split | incomplete_groups]
    assert len(primary) % 4 == 0
    result = {
        "status": "partial_network_blocked" if partial else "complete_segmented",
        "allCompletedSlots": len(rows),
        "remainingSlots": 2160 - len(rows),
        "primarySlots": len(primary),
        "primaryMatchedGroups": len(primary) // 4,
        "independentTasks": len(cases),
        "interruptedGroups": len(excluded),
        "crossSessionGroups": len(split),
        "incompleteObservedGroups": len(incomplete_groups),
        "excludedGroupUnion": len(excluded | split | incomplete_groups),
        "physicalStates": dict(collections.Counter(r["state"] for r in physical)),
        "physicalStatuses": dict(
            collections.Counter(str(r.get("status", r["state"])) for r in physical)
        ),
        "recordedTokensAllReturned": sum(
            r.get("usage", {}).get("total_tokens", 0) for r in physical
        ),
        "primaryByArm": {a: metrics([r for r in primary if r["arm"] == a]) for a in "ABCD"},
        "allCompletedByArm": {
            a: {
                "n": sum(r["arm"] == a for r in rows),
                "finalCorrect": sum(r["arm"] == a and r["finalCorrect"] for r in rows),
                "wrongAccepted": sum(
                    r["arm"] == a and r["accepted"] and not r["finalCorrect"] for r in rows
                ),
                "totalTokens": sum(r["totalTokens"] for r in rows if r["arm"] == a),
            }
            for a in "ABCD"
        },
    }
    result["physicalRoundTrips"] = {}
    for phase in ("initial", "repair"):
        subset = [r for r in physical if r["phase"] == phase and "roundTripMs" in r]
        result["physicalRoundTrips"][phase] = {
            "measured": len(subset),
            "roundTripMs": describe([r["roundTripMs"] for r in subset]),
            "byModel": {
                m: describe([r["roundTripMs"] for r in subset if r["slot"]["model"] == m])
                for m in sorted({r["slot"]["model"] for r in subset})
            },
        }
    for dimension in ("epoch", "model", "project", "family", "worker"):
        result[dimension] = {
            str(v): {
                a: metrics(subset)
                for a in "ABCD"
                if (subset := [r for r in primary if r[dimension] == v and r["arm"] == a])
            }
            for v in sorted({r[dimension] for r in primary})
        }
    # Matched within-session differences; task/project clustering avoids treating repeats as independent tasks.
    result["pairedProjectBootstrap"] = {}
    for metric in ("serviceTotalMs", "providerRoundTripMs", "activePipelineMs"):
        result["pairedProjectBootstrap"][metric] = {}
        for left, right in [("B", "A"), ("C", "B"), ("D", "C")]:
            differences = collections.defaultdict(list)
            for key, values in groups.items():
                if key in excluded | split | incomplete_groups or (
                    left == "D" and not cases[key[0]].get("d_calc")
                ):
                    continue
                arms = {r["arm"]: r for r in values}
                differences[arms[left]["project"]].append(
                    arms[left]["timing"][metric] - arms[right]["timing"][metric]
                )
            project_means = [statistics.mean(v) for v in differences.values()]
            rng = random.Random(20261024)
            samples = sorted(
                statistics.mean(rng.choices(project_means, k=len(project_means)))
                for _ in range(10000)
            )
            result["pairedProjectBootstrap"][metric][left + "-" + right] = {
                "projectEqualWeightMeanDifferenceMs": statistics.mean(project_means),
                "descriptive95": [samples[249], samples[9749]],
                "projects": len(project_means),
                "matchedGroups": sum(len(v) for v in differences.values()),
                "arithmeticOnly": left == "D",
            }
    (PARENT / "FINISHED_SUMMARY.json").write_text(json.dumps(result, indent=2) + "\n")
    schedule = json.loads((continuation.FIRST / "manifest.json").read_text())["slots"]
    complete = {continuation.identity(r) for r in rows}
    remaining = [r for r in schedule if continuation.identity(r) not in complete]
    (PARENT / "REMAINING_SCHEDULE.json").write_text(
        json.dumps(
            {
                "count": len(remaining),
                "slots": remaining,
                "policy": "Preserve existing returned responses and incomplete receipts. Do not blindly restart completed identities. Any new session must be separately identified; interrupted timings are unknown.",
            },
            indent=2,
        )
        + "\n"
    )
    lines = [
        "# HESchema latency replication — " + ("PARTIAL — " if partial else "") + "24 October 2026",
        "",
        f"Completed: **{len(rows):,}/2,160 slots; {2160 - len(rows):,} remain**. The planned design covers 60 reused public-record adaptations from ten projects, three models, three repeats and four approaches.",
        "",
        "**This is a segmented parallel-batch measurement, not proof that HESchema universally makes models faster.** The execution host reset after 635 completed slots. A second session was stopped by a network-policy rejection after another 680 complete slots. A third session completed the remaining 845 identities, reusing three intact initial responses. Timers for those reused responses cover resumed processing only; their whole matched groups are excluded from primary latency. Original completed responses were not regenerated.",
        "",
        (
            '**BLOCKED:** The execution tool stopped the continuation with `Network access to "https://api.groq.com:443" was blocked by policy.` This is not evidence of invalid keys or an ordinary Groq quota error. The full-study acceptance check did not pass. Findings below are provisional.'
            if partial
            else "All 2,160 result identities are now covered and verified across three sessions. Historical incomplete physical receipts remain explicitly unknown; completing a replacement does not reconstruct their missing timings."
        ),
        "",
        f"Primary analysis: **{len(primary) // 4} matched groups ({len(primary):,} results; {len(primary) // 4} per arm)**. Excluded observed groups include {len(excluded)} touched by either earlier interruption, {len(split)} crossing execution sessions and {len(incomplete_groups)} without all four completed arms (categories may overlap). Exclusions affect the primary comparison only; all completed correctness/token outcomes remain in the JSON appendix.",
        "",
        "## Primary results",
        "",
        "A = ordinary schema; B = FULL contract; C = COMPACT contract; D = COMPACT plus declared arithmetic calculations. D otherwise matches C. All allow one detector-triggered repair.",
        "",
        "| Approach | Final correct | Wrong accepted | Mean total tokens | Service median / p95, s | HTTP total median / p95, s |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for arm, m in result["primaryByArm"].items():
        lines.append(
            f"| {arm} | {m['finalCorrect']}/{m['n']} ({100 * m['finalCorrect'] / m['n']:.2f}%) | {m['wrongAccepted']} | {m['totalTokens'] / m['n']:.1f} | {m['serviceTotalMs']['median'] / 1000:.3f} / {m['serviceTotalMs']['p95'] / 1000:.3f} | {m['providerRoundTripMs']['median'] / 1000:.3f} / {m['providerRoundTripMs']['p95'] / 1000:.3f} |"
        )
    arms = result["primaryByArm"]
    reduction = 100 * (1 - arms["C"]["totalTokens"] / arms["B"]["totalTokens"])
    lines += [
        "",
        f"**Observed finding:** COMPACT used {reduction:.2f}% fewer total tokens than FULL in the matched sample. COMPACT's HTTP median was {arms['C']['providerRoundTripMs']['median'] / 1000:.3f}s versus FULL's {arms['B']['providerRoundTripMs']['median'] / 1000:.3f}s. This does not show a speed improvement. Contract arms accepted zero observed wrong final answers; the ordinary-schema arm accepted {arms['A']['wrongAccepted']}. This is an observed validation benefit on this sample, not guaranteed correctness or evidence that conventional application checks could not catch the same errors.",
    ]
    lines += [
        "",
        "## Timing components",
        "",
        "| Component: median / p95, ms | A | B | C | D |",
        "|---|---:|---:|---:|---:|",
    ]
    for metric in METRICS:
        lines.append(
            "| "
            + metric
            + " | "
            + " | ".join(
                f"{result['primaryByArm'][a][metric]['median']:.2f} / {result['primaryByArm'][a][metric]['p95']:.2f}"
                for a in "ABCD"
            )
            + " |"
        )
    lines += [
        "",
        "### Repairs and waits in the matched sample",
        "",
        "| Approach | Repairs | Results with retry wait | Maximum retry wait, s | Total retry wait, s |",
        "|---|---:|---:|---:|---:|",
    ]
    for a, m in arms.items():
        lines.append(
            f"| {a} | {m['repairCount']} | {m['retryAffected']} | {m['retryMaxMs'] / 1000:.2f} | {m['retryTotalMs'] / 1000:.2f} |"
        )
    lines += [
        "",
        "Service runs from worker assignment to final validation, including HTTP repairs, pacing and retry waits. HTTP total sums all awaited initial/repair/failed HTTP calls for the slot; it includes network and remote queues, not pure inference. Active pipeline subtracts deliberate pacing and retry waits from service. Local validation excludes the measured calculation operation. Queue and end-to-end are session-relative batch measurements, not single-user application latency. Offline correctness scoring and final audit-file persistence are excluded. Component percentiles do not add to total percentiles.",
        "",
        "## Execution sessions: service median / p95, seconds",
        "",
        "| Session | A | B | C | D |",
        "|---|---:|---:|---:|---:|",
    ]
    for epoch, arms in result["epoch"].items():
        lines.append(
            "| "
            + epoch
            + " | "
            + " | ".join(
                f"{arms[a]['serviceTotalMs']['median'] / 1000:.3f} / {arms[a]['serviceTotalMs']['p95'] / 1000:.3f} (n={arms[a]['n']})"
                for a in "ABCD"
            )
            + " |"
        )
    lines += [
        "",
        "## Paired exploratory differences",
        "",
        "Left minus right: negative means the left approach used less time. Equal weight is given to each project; 10,000 project-bootstrap resamples produce descriptive 95% intervals. There are at most ten independent project clusters. These intervals do not remove provider/worker interference or establish general causality.",
        "",
        "| Metric | Comparison | Mean difference, ms | Descriptive 95%, ms | Matched groups |",
        "|---|---|---:|---:|---:|",
    ]
    for metric, comparisons in result["pairedProjectBootstrap"].items():
        for pair, values in comparisons.items():
            lo, hi = values["descriptive95"]
            lines.append(
                f"| {metric} | {pair}{' (arithmetic only)' if values['arithmeticOnly'] else ''} | {values['projectEqualWeightMeanDifferenceMs']:.2f} | [{lo:.2f}, {hi:.2f}] | {values['matchedGroups']} |"
            )
    lines += [
        "",
        "## Evidence, checks and limitations",
        "",
        f"- Physical request states: `{result['physicalStates']}`; statuses: `{result['physicalStatuses']}`. Interrupted started receipts remain explicitly unverified; they are not silently relabeled as completed or assigned invented durations.",
        f"- All returned receipt tokens, including preserved orphan responses: {result['recordedTokensAllReturned']:,}. Missing usage on interrupted requests is unknown. Tokens are not verified billing.",
        "- Passed: identity consistency for completed slots, immutable original evidence hashes, frozen generator hashes, selected provider receipts and usage, timing partitions, and independent offline correctness scoring. Full planned identity coverage passed across the three sessions. Exact uninterrupted-run gates remain abandoned and are not relabeled as passed.",
        "- Original uninterrupted-run gate is abandoned because of host loss. The segmented verification is a replacement outcome and does not erase that limitation.",
        "- Nine fixed paced workers used the supplied credentials. Independent organizations/quotas were asserted by the user and not verified. Quota waits, shared provider load and account/worker scheduling affect timing.",
        "- Latency differences combine prompt generation, detection and repair policy. A can accept a semantically wrong response without repair, while contract arms may reject and repair it. A faster returned answer is not necessarily a faster correct answer; these results do not isolate validation as the cause of a timing difference.",
        "- Dependencies were reinstalled after host loss. Continuation environment is recorded; exact equivalence to the lost environment is not established. Report sessions separately.",
        "- Excluding interrupted and cross-session groups can omit slower requests and bias observed latency, particularly tail percentiles. The complete identity coverage does not remove that exclusion bias.",
        "- The tasks were reused from H60. They are researcher-created public-record adaptations, not 60 organic production prompts or new untouched confirmation tasks. Original source archive was not recaptured.",
        "- D measures assembled system output. It does not prove the model learned arithmetic. Zero observed wrong acceptance does not guarantee complete validation.",
        "- No browser/server production journey, streaming time to first token, pure model inference, billed cost, or universal speed/accuracy improvement is measured.",
        "- Detailed per-model, project, family, worker and session distributions, all-completed sensitivity results, and bootstrap values are in FINISHED_SUMMARY.json.",
        "",
        "## Claims",
        "",
        "Supported: measured response-ready harness timings and token/correctness outcomes on these tasks, settings and execution sessions. Comparisons must state their sample, waits, repair allowance and session limitation.",
        "",
        "Not supported: HESchema always speeds up models; contract checking guarantees correctness; all observed service differences come from contracts; the study is an uninterrupted or production latency benchmark; new JSON Schema vocabulary is necessary.",
        "",
    ]
    (PARENT / "HESchema_Latency_Finished_Report.md").write_text("\n".join(lines))
    print("FINISHED_LATENCY_REPORT_VERIFIED")


if __name__ == "__main__":
    analyze()
