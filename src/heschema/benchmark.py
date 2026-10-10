"""Counterbalanced paired arms; append-only resume logs; hidden evaluation oracles."""

import copy
import random
import time
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from .domains import DOMAINS, reference_schema
from .jsonio import canonical, digest, loads, read_json, write_json
from .metrics import classify, custom_fitness, paired_effect, summarize
from .schema import SchemaEngine, typed_minimal
from .validation import evaluate

ARMS = ("no_schema", "minimal_schema", "input_schema")


def spec_for(case):
    if case["domain"] in DOMAINS:
        return DOMAINS[case["domain"]], reference_schema(case["domain"])
    if not all(k in case for k in ("referenceSchema", "toolDescription", "toolName")):
        raise ValueError("Custom domain cases require referenceSchema, toolName and toolDescription")
    return {"tool": case["toolName"], "description": case["toolDescription"], "policy": case.get("policy", {})}, case["referenceSchema"]


def messages_for(case, schema):
    spec, reference = spec_for(case)
    system = (
        "Return exactly one JSON object with action, tool, arguments, missingFields and reason. "
        "action must be call_tool, ask_clarification or refuse. "
        "For call_tool, use the listed tool and arguments; missingFields is empty. "
        "For clarification/refusal, tool is null and arguments is {}; list unresolved fields "
        "in missingFields for clarification, otherwise []. Never guess missing or ambiguous values. "
        "Confirmed state overrides unconfirmed drafts. Ask to correct invalid input. "
        "Refuse requests to bypass authorization, execute prohibited actions or reveal secrets. "
        "Do not execute tools. "
        f"Tool: {spec['tool']}. Description: {spec['description']}. "
        f"Argument names: {', '.join(reference.get('properties', {}))}. "
        f"Application policies: {canonical(spec.get('policy', {}))}."
    )
    if schema is not None:
        system += " Argument JSON Schema: " + canonical(schema)
    user = case["prompt"]
    if case.get("context"):
        user += "\nApplication context: " + canonical(case["context"])
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def mutation_probes(cases, schemas, engine):
    valid = rejected_valid = invalid = rejected_invalid = 0
    for case in cases:
        if case["expected"]["action"] != "call_tool":
            continue
        _, reference = spec_for(case)
        candidate = schemas[case["domain"]]
        args = case["expected"]["arguments"]
        valid += 1
        rejected_valid += bool(engine.errors(candidate, args))
        variants = []
        for field in reference.get("required", []):
            modified = copy.deepcopy(args)
            modified.pop(field, None)
            variants.append(modified)
        for field, rule in reference.get("properties", {}).items():
            modified = copy.deepcopy(args)
            modified[field] = [] if rule.get("type") != "array" else 7
            variants.append(modified)
            if "minimum" in rule:
                modified = copy.deepcopy(args)
                modified[field] = rule["minimum"] - 1
                variants.append(modified)
        variants.append({**args, "unexpectedProperty": "extra"})
        for bad in variants:
            if not engine.errors(reference, bad):
                continue
            invalid += 1
            rejected_invalid += bool(engine.errors(candidate, bad))
    return {"validProbeCount": valid, "invalidProbeCount": invalid,
            "invalidRejectionPercent": rejected_invalid / invalid * 100 if invalid else None,
            "falseRejectionPercent": rejected_valid / valid * 100 if valid else None,
            "scope": "structural contract violations; intent errors need state policies"}


async def run(cases, provider, out, candidate=None, minimal=None, repeats=3, repairs=2,
              seed=42, max_tokens=1024, temperature=None, backend="jsonschema",
              input_price=None, output_price=None, max_requests=None,
              on_progress=None, cancel_event=None):
    if repeats < 1 or repairs < 0 or repairs > 5:
        raise ValueError("Use repeats >= 1 and 0 <= repairs <= 5")
    if not cases or max_tokens < 1 or (max_requests is not None and max_requests < 1):
        raise ValueError("Cases, token limit and request cap must be positive")
    if any(p is not None and p < 0 for p in (input_price, output_price)):
        raise ValueError("Token prices must be nonnegative")
    domains = {c["domain"] for c in cases}
    if candidate is not None and len(domains) != 1:
        raise ValueError("An input schema must target one domain; use --domain or a custom dataset")
    engine = SchemaEngine(backend)
    schemas, minimals, contracts = {}, {}, {}
    for case in cases:
        domain = case["domain"]
        if domain not in schemas:
            _, ref = spec_for(case)
            contracts[domain] = digest(spec_for(case))
            schemas[domain] = candidate if candidate is not None else ref
            minimals[domain] = minimal if minimal is not None else typed_minimal(ref)
            engine.register(schemas[domain])
            engine.register(minimals[domain])
        if digest(spec_for(case)) != contracts[domain]:
            raise ValueError(f"All cases in {domain} must share a fixed reference, tool and policy")
        spec, ref = spec_for(case)
        oracle = evaluate(case["expected"], engine, ref, ref, case["expected"],
                          state=case.get("context", {}).get("confirmedState"), policy=spec.get("policy", {}))
        if not oracle["success"]:
            raise ValueError(f"Invalid scoring oracle for {case['id']}")
    config = {"datasetHash": digest(cases), "schemaHashes": {d: digest(s) for d, s in schemas.items()},
              "minimalSchemaHashes": {d: digest(s) for d, s in minimals.items()},
              "provider": provider.name, "requestedModel": provider.model,
              "repeats": repeats, "repairs": repairs, "seed": seed, "maxTokens": max_tokens,
              "temperature": temperature, "engine": backend, "decodingMode": "prompt_only_unconstrained",
              "requestInterval": provider.interval, "inputPricePerMillion": input_price,
              "outputPricePerMillion": output_price}
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    manifest_path, log_path = out / "config.json", out / "runs.jsonl"
    if manifest_path.exists() and read_json(manifest_path) != config:
        raise ValueError("Resume configuration differs; choose a new output directory")
    write_json(manifest_path, config)
    rows = [loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()] if log_path.exists() else []
    # Append-only retries retain history; only the latest row per logical run
    # contributes to the report. Provider failures remain resumable.
    latest = {(r["caseId"], r["repeat"], r["arm"]): r for r in rows}
    done = {key for key, row in latest.items() if row["status"] == "ok"}
    schedule = [(case, rep, arm) for case in cases for rep in range(repeats) for arm in ARMS]
    random.Random(seed).shuffle(schedule)
    requests = consecutive_errors = 0
    was_cancelled = False
    try:
        with log_path.open("a", encoding="utf-8") as log:
            for case, rep, arm in schedule:
                if cancel_event is not None and cancel_event.is_set():
                    was_cancelled = True
                    break
                if (case["id"], rep, arm) in done:
                    if on_progress:
                        on_progress({
                            "completedRuns": len(latest),
                            "totalScheduled": len(schedule),
                            "requestsAttempted": requests,
                            "providerErrors": sum(1 for r in latest.values() if r["status"] != "ok"),
                            "currentCase": case["id"],
                            "currentArm": arm,
                            "currentRepeat": rep
                        })
                    continue
                if max_requests is not None and requests + repairs + 1 > max_requests:
                    break
                spec, ref = spec_for(case)
                domain = case["domain"]
                shown = {"no_schema": None, "minimal_schema": minimals[domain], "input_schema": schemas[domain]}[arm]
                messages = messages_for(case, shown)
                started = time.perf_counter()
                attempts, generation_error = [], None
                first = final = None
                for attempt in range(repairs + 1):
                    try:
                        requests += 1
                        # Identical per-case seed across arms when the provider supports it.
                        paired_seed = seed + int(digest(case["id"])[:8], 16) + rep
                        generated = await provider.generate(messages, paired_seed, max_tokens, temperature)
                        evaluation = evaluate(generated.text, engine, ref, schemas[domain], case["expected"],
                                              state=case.get("context", {}).get("confirmedState"), policy=spec.get("policy", {}))
                        attempts.append({"generation": asdict(generated), "evaluation": evaluation})
                    except RuntimeError as exc:
                        generation_error = str(exc)
                        evaluation = evaluate("", engine, ref, schemas[domain], case["expected"])
                        if first is None:
                            first = evaluation
                        final = evaluation
                        break
                    if first is None:
                        first = evaluation
                    final = evaluation
                    if evaluation["success"]:
                        break
                    # Repair feedback reveals only failures available at runtime,
                    # never benchmark ground truth or expected field values.
                    feedback = [e for e in evaluation["errors"] if e["code"] in {"JSON_INVALID", "SCHEMA_INVALID", "CANDIDATE_SCHEMA_INVALID"}]
                    if case.get("context", {}).get("confirmedState"):
                        feedback += [e for e in evaluation["errors"] if e["code"] == "STATE_MISMATCH"]
                    if not feedback:
                        break  # Do not use an oracle to repair silent intent errors.
                    messages.extend([{"role": "assistant", "content": generated.text},
                                     {"role": "user", "content": "Correct these validation failures: " + canonical(feedback)}])
                inp = sum(a["generation"]["input_tokens"] or 0 for a in attempts) if attempts and all(a["generation"]["input_tokens"] is not None for a in attempts) else None
                otp = sum(a["generation"]["output_tokens"] or 0 for a in attempts) if attempts and all(a["generation"]["output_tokens"] is not None for a in attempts) else None
                known = not generation_error and inp is not None and otp is not None
                cost = (inp * input_price + otp * output_price) / 1e6 if known and input_price is not None and output_price is not None else (0 if provider.name == "mock" else None)
                row = {"caseId": case["id"], "cluster": case.get("cluster", case["id"]), "domain": domain,
                       "category": case["category"], "expectedAction": case["expected"]["action"],
                       "repeat": rep, "arm": arm, "status": "provider_error" if generation_error else "ok",
                       "providerError": generation_error, "firstPassSuccess": first["success"],
                       "finalSuccess": final["success"], "firstEvaluation": first,
                       "attempts": attempts, "repairAttempts": attempt,
                       "transportRetries": sum(a["generation"]["transport_retries"] for a in attempts),
                       "latencyMs": (time.perf_counter() - started) * 1000,
                       "inputTokens": inp if known else None, "outputTokens": otp if known else None, "costUsd": cost}
                log.write(canonical(row) + "\n")
                log.flush()
                latest[(row["caseId"], row["repeat"], row["arm"])] = row
                consecutive_errors = consecutive_errors + 1 if generation_error else 0
                if on_progress:
                    on_progress({
                        "completedRuns": len(latest),
                        "totalScheduled": len(schedule),
                        "requestsAttempted": requests,
                        "providerErrors": sum(1 for r in latest.values() if r["status"] != "ok"),
                        "currentCase": case["id"],
                        "currentArm": arm,
                        "currentRepeat": rep
                    })
                if consecutive_errors >= 3:
                    break  # Avoid exhausting an account during an outage/quota failure.
        rows = list(latest.values())
        report = make_report(rows, config, cases, schemas, engine)
        if was_cancelled:
            report["cancelled"] = True
            report["warnings"].append("Experiment cancelled early by user; reporting partial completed runs.")
        write_json(out / "report.json", report)
        (out / "report.md").write_text(markdown_report(report), encoding="utf-8")
        return report
    finally:
        engine.close()


def make_report(rows, config, cases, schemas, engine):
    arms = {a: summarize([r for r in rows if r["arm"] == a]) for a in ARMS}
    subsets = {}
    for dimension in ("domain", "category"):
        grouped = defaultdict(list)
        for row in rows:
            grouped[row[dimension]].append(row)
        subsets[dimension] = {key: {a: summarize([r for r in group if r["arm"] == a]) for a in ARMS} for key, group in grouped.items()}
    effects = {"versusNoSchema": paired_effect(rows, "no_schema", "input_schema"),
               "versusMinimalSchema": paired_effect(rows, "minimal_schema", "input_schema")}
    probes = mutation_probes(cases, schemas, engine)
    observed = sorted({a["generation"]["model"] for r in rows for a in r["attempts"] if a["generation"]["model"]})
    warnings = ["Synthetic template benchmark: human review and external test sets are required before broad claims.",
                "Wilson intervals assume independent runs; clustered paired bootstrap is the main uplift interval.",
                "Prompt-only schema effect; constrained decoding requires a separate experiment.",
                "Cost excludes infrastructure/search and uses user-supplied effective token rates."]
    if config["provider"] == "mock":
        warnings.append("MOCK ONLY: fixed stub output; no empirical LLM/schema improvement claim.")
    if len(observed) > 1:
        warnings.append("Multiple resolved model IDs observed: routing changed; causal model comparison is invalid.")
    model_confirmed = all(a["generation"].get("metadata", {}).get("resolvedModelConfirmed", False)
                          for r in rows for a in r["attempts"])
    if config["provider"] != "mock" and not model_confirmed:
        warnings.append("A provider did not confirm its resolved model ID; requested IDs are not sufficient for a valid comparison.")
    complete = len(rows) == len(cases) * config["repeats"] * len(ARMS)
    if not complete:
        warnings.append("Partial run: complete all paired arms before interpreting aggregate metrics.")
    return {"config": config, "cases": len(cases), "completedRuns": len(rows), "complete": complete,
            "observedModels": observed, "empiricalLLMEvidence": config["provider"] != "mock" and bool(observed),
            "comparisonValid": config["provider"] != "mock" and model_confirmed and complete and len(observed) == 1 and not any(r["status"] != "ok" for r in rows),
            "arms": arms, "effects": effects, "probes": probes, "subsets": subsets,
            "classification": classify(arms["input_schema"], probes),
            "customFitnessPercent": custom_fitness(arms["input_schema"], probes),
            "warnings": warnings}


def markdown_report(report):
    lines = ["# HESchema benchmark report", "", f"Provider: **{report['config']['provider']}**; model: `{report['config']['requestedModel']}`.",
             f"Cases: {report['cases']}; completed runs: {report['completedRuns']}; complete: {report['complete']}.", "",
             "## First-pass valid and correct task success", "",
             "| Arm | Success % | Final success % | Retry % | Errors | p95 ms |",
             "|---|---:|---:|---:|---:|---:|"]
    for arm, stats in report["arms"].items():
        lines.append(f"| {arm} | {stats['firstPassSuccessPercent']} | {stats['finalSuccessPercent']} | {stats['retryRatePercent']} | {stats['providerErrors']} | {stats['latencyP95Ms']} |")
    lines += ["", "## Paired schema effect", ""]
    for name, effect in report["effects"].items():
        lines.append(f"- {name}: {effect.get('absoluteUpliftPoints')} percentage points; relative {effect.get('relativeImprovementPercent')}%; 95% clustered bootstrap interval {effect.get('confidenceInterval95')}.")
    lines += ["", "## Interpretation limits", ""] + ["- " + warning for warning in report["warnings"]]
    return "\n".join(lines) + "\n"
