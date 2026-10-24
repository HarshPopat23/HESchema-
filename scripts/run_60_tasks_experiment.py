"""Parallel 60-Task 4-Arm Experiment Runner for HESchema prospective confirmation.

Uses 6 Groq API keys concurrently with individual rate-limiting, strict validation,
repair handling, and streaming checkpointing.
"""

import argparse
import asyncio
import copy
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from heschema.contracts import Contract
from heschema.context_schema import effective_schema, trusted_information
from heschema.contract_prompt import contract_messages
from heschema.calculations import calculation_input_schema, calculation_plan, validate_with_calculations
from heschema.jsonio import canonical, loads
from heschema.schema import SchemaEngine
from heschema.validation import validate_contract
from jsonschema import Draft202012Validator, FormatChecker

DATA_DIR = ROOT / "research" / "confirmation-60-v1"
RUNS_DIR = DATA_DIR / "runs"

MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b"
]

ARMS = ["A", "B", "C", "D"]
REPEATS = 3
SEED = 20261021

def get_groq_keys():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
    keys_str = os.getenv("GROQ_API_KEYS", os.getenv("GROQ_API_KEY", ""))
    keys = [k.strip() for k in keys_str.split(",") if k.strip()]
    if not keys:
        raise ValueError("Please set GROQ_API_KEYS or GROQ_API_KEY in environment or .env")
    return keys


def build_schedule(cases, seed=SEED):
    rng = random.Random(seed)
    groups = [(case["id"], model, repeat) for case in cases
              for model in MODELS for repeat in range(REPEATS)]
    rng.shuffle(groups)
    slots = []
    for case_id, model, repeat in groups:
        arms = list(ARMS)
        rng.shuffle(arms)
        for arm in arms:
            slots.append({
                "caseId": case_id,
                "model": model,
                "repeat": repeat,
                "arm": arm
            })
    return slots


def slot_key(s):
    return (s["caseId"], s["model"], s["repeat"], s["arm"])


def build_messages_for_arm(case, arm):
    contract = Contract(**case["contract"])
    snapshot = case["snapshot"]
    prompt = case["prompt"]

    if arm == "A":
        # Arm A: Ordinary Draft 2020-12 schema only
        system_content = (
            "Return only whole JSON. Never execute tools. "
            "Output JSON Schema: " + canonical(contract.schema) +
            "\nTrusted facts: " + canonical(trusted_information(snapshot))
        )
        return [{"role": "system", "content": system_content}, {"role": "user", "content": prompt}], contract

    eff_schema, evidence = effective_schema(contract, snapshot)

    if arm == "B":
        # Arm B: FULL contract prompt
        msgs = contract_messages(contract, snapshot, evidence, eff_schema, prompt, style="full")
        return msgs, contract

    if arm == "C":
        # Arm C: COMPACT contract prompt
        msgs = contract_messages(contract, snapshot, evidence, contract.schema, prompt, style="compact")
        return msgs, contract

    if arm == "D":
        # Arm D: Selective calculations
        plan = case.get("d_calc")
        if plan:
            contract_d = Contract(**{
                **case["contract"],
                "relationships": [
                    {**r, "compute": "application"} if r.get("id") == plan[0].get("id") else r
                    for r in case["contract"].get("relationships", [])
                ]
            })
            plan_d = calculation_plan(contract_d)
            in_schema = calculation_input_schema(contract_d.schema, plan_d)
            msgs = contract_messages(contract_d, snapshot, evidence, in_schema, prompt, style="compact")
            return msgs, contract_d
        else:
            msgs = contract_messages(contract, snapshot, evidence, contract.schema, prompt, style="compact")
            return msgs, contract

    raise ValueError(f"Unknown arm: {arm}")


def build_repair_message(original_messages, prev_text, error_msg):
    capped_err = (error_msg or "Validation rejected the response.")[:1000]
    return list(original_messages) + [
        {"role": "assistant", "content": prev_text},
        {"role": "user", "content": (
            "The previous response was rejected by validation:\n"
            f"{capped_err}\n\n"
            "Please correct the errors and return only the valid whole JSON object."
        )}
    ]


def evaluate_attempt(raw_text, arm, case, contract, engine):
    snapshot = case["snapshot"]
    errors = []
    parsed = None
    json_valid = False

    try:
        parsed = loads(raw_text) if isinstance(raw_text, str) else loads(canonical(raw_text))
        json_valid = True
    except Exception as e:
        errors.append(f"JSON invalid: {str(e)[:200]}")

    if not json_valid:
        return {
            "accepted": False,
            "oracleCorrect": False,
            "schemaAccepted": False,
            "parsed": None,
            "error": "JSON parse failed",
            "diagnostics": errors
        }

    # Arm A Detector: Standard Draft 2020-12 schema validator only
    if arm == "A":
        v = Draft202012Validator(contract.schema, format_checker=FormatChecker())
        schema_errors = [e.message for e in v.iter_errors(parsed)]
        detector_accepted = (len(schema_errors) == 0)
        schema_accepted = detector_accepted

        # Oracle evaluation: Complete contract validation (facts bindings + relationships)
        oracle_res = validate_contract(raw_text, engine, contract, snapshot)
        oracle_correct = bool(oracle_res["accepted"] and oracle_res.get("success", False))

        diag = "\n".join(schema_errors) if schema_errors else ""
        return {
            "accepted": detector_accepted,
            "oracleCorrect": oracle_correct,
            "schemaAccepted": schema_accepted,
            "parsed": parsed,
            "error": schema_errors[0] if schema_errors else None,
            "diagnostics": diag
        }

    # Arm D Detector: validate_with_calculations
    if arm == "D" and case.get("d_calc"):
        res = validate_with_calculations(raw_text, engine, contract, snapshot)
        detector_accepted = bool(res["accepted"])
        oracle_correct = bool(res["accepted"] and res.get("success", False))
        diag_errs = [e.get("message", str(e)) for e in res.get("errors", [])]
        return {
            "accepted": detector_accepted,
            "oracleCorrect": oracle_correct,
            "schemaAccepted": bool(res.get("referenceSchemaValid")),
            "parsed": res.get("parsed"),
            "error": diag_errs[0] if diag_errs else None,
            "diagnostics": "\n".join(diag_errs)
        }

    # Arm B & C Detector: validate_contract (HESchema full verification)
    res = validate_contract(raw_text, engine, contract, snapshot)
    detector_accepted = bool(res["accepted"])
    oracle_correct = bool(res["accepted"] and res.get("success", False))
    diag_errs = [e.get("message", str(e)) for e in res.get("errors", [])]
    return {
        "accepted": detector_accepted,
        "oracleCorrect": oracle_correct,
        "schemaAccepted": bool(res.get("referenceSchemaValid")),
        "parsed": res.get("parsed"),
        "error": diag_errs[0] if diag_errs else None,
        "diagnostics": "\n".join(diag_errs)
    }


class GroqClient:
    def __init__(self, key: str, worker_id: int):
        self.key = key
        self.worker_id = worker_id
        self.client = httpx.AsyncClient(timeout=60.0)

    async def generate(self, messages, model, max_tokens=2048, temperature=0.0):
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json"
        }
        body = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        for attempt in range(4):
            try:
                t0 = time.perf_counter()
                resp = await self.client.post(url, headers=headers, json=body)
                latency_ms = (time.perf_counter() - t0) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    choice = data["choices"][0]
                    usage = data.get("usage", {})
                    return {
                        "text": choice["message"]["content"],
                        "input_tokens": usage.get("prompt_tokens"),
                        "output_tokens": usage.get("completion_tokens"),
                        "latency_ms": latency_ms,
                        "status_code": 200,
                        "error": None
                    }
                else:
                    err_msg = resp.text
                    try:
                        err_data = resp.json()
                        err_msg = err_data.get("error", {}).get("message", resp.text)
                    except Exception:
                        pass
                    return {
                        "text": "",
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "latency_ms": latency_ms,
                        "status_code": resp.status_code,
                        "error": err_msg
                    }
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                if attempt == 3:
                    return {
                        "text": "",
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "latency_ms": 0,
                        "status_code": 503,
                        "error": f"Network transport error: {str(exc)}"
                    }
                await asyncio.sleep(2.0 * (attempt + 1))

    async def close(self):
        await self.client.aclose()


def load_existing_runs(path: Path):
    if not path.exists():
        return {}
    completed = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                k = (row["caseId"], row["model"], row["repeat"], row["arm"])
                completed[k] = row
            except Exception:
                pass
    return completed


def compute_summary(rows, total_slots):
    by_arm = {}
    for arm in ARMS:
        subset = [r for r in rows if r["arm"] == arm]
        n = len(subset)
        if n == 0:
            by_arm[arm] = {"slots": 0}
            continue
        first_corr = sum(1 for r in subset if r["firstCorrect"])
        final_corr = sum(1 for r in subset if r["finalCorrect"])
        false_accept = sum(1 for r in subset if r["falseAcceptance"])
        total_inp = sum(r["totalInputTokens"] for r in subset)
        total_out = sum(r["totalOutputTokens"] for r in subset)
        by_arm[arm] = {
            "slots": n,
            "firstCorrect": first_corr,
            "firstCorrectPct": round(first_corr / n * 100, 2),
            "finalCorrect": final_corr,
            "finalCorrectPct": round(final_corr / n * 100, 2),
            "falseAcceptance": false_accept,
            "falseAcceptancePct": round(false_accept / n * 100, 2),
            "meanInputTokens": round(total_inp / n, 1),
            "meanOutputTokens": round(total_out / n, 1)
        }

    return {
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "totalCompleted": len(rows),
        "totalPlanned": total_slots,
        "completionPct": round(len(rows) / total_slots * 100, 2) if total_slots else 0,
        "byArm": by_arm
    }


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=float, default=6.0, help="Pacing per worker in seconds")
    parser.add_argument("--max-slots", type=int, default=None, help="Limit slots for testing")
    args = parser.parse_args()

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    cases_file = DATA_DIR / "cases.json"
    cases = json.loads(cases_file.read_text(encoding="utf-8"))
    by_id = {c["id"]: c for c in cases}

    slots = build_schedule(cases)
    if args.max_slots:
        slots = slots[:args.max_slots]

    runs_path = RUNS_DIR / "runs.jsonl"
    summary_path = RUNS_DIR / "summary.json"
    events_path = RUNS_DIR / "events.jsonl"

    existing = load_existing_runs(runs_path)
    pending = [s for s in slots if slot_key(s) not in existing]
    all_rows = list(existing.values())

    keys = get_groq_keys()
    print(f"=== HESchema 60-Task Experiment ===")
    print(f"Total planned slots: {len(slots)}")
    print(f"Already completed: {len(existing)}")
    print(f"Pending to execute: {len(pending)}")
    print(f"Parallel workers: {len(keys)}")
    print(f"Pacing per worker: {args.interval}s")
    print(f"Output directory: {RUNS_DIR}")
    print("===================================\n")

    queue = asyncio.Queue()
    for s in pending:
        queue.put_nowait(s)

    engine = SchemaEngine()
    lock = asyncio.Lock()

    async def worker(worker_id: int, key: str):
        client = GroqClient(key, worker_id)
        last_req_time = 0.0

        try:
            while True:
                try:
                    slot = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

                client.slot = dict(slot)
                case = by_id[slot["caseId"]]
                arm = slot["arm"]
                model = slot["model"]
                repeat = slot["repeat"]

                # Pacing wait
                elapsed = time.monotonic() - last_req_time
                wait_s = max(0.0, args.interval - elapsed)
                if wait_s > 0:
                    await asyncio.sleep(wait_s)

                msgs, contract = build_messages_for_arm(case, arm)

                # Attempt 1 (Initial Generation)
                last_req_time = time.monotonic()
                gen1 = await client.generate(msgs, model)

                # Handle 429 rate limit backoff
                if gen1["status_code"] == 429:
                    async with lock:
                        with events_path.open("a", encoding="utf-8") as ef:
                            ef.write(json.dumps({
                                "event": "rate_limit_backoff",
                                "worker": worker_id,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "slot": slot
                            }) + "\n")
                    print(f"Worker {worker_id}: 429 Rate limit encountered, cooling down 60s...")
                    await asyncio.sleep(60.0)
                    gen1 = await client.generate(msgs, model)

                eval1 = evaluate_attempt(gen1["text"], arm, case, contract, engine)
                first_accepted = eval1["accepted"]
                first_correct = eval1["oracleCorrect"]

                final_accepted = first_accepted
                final_correct = first_correct
                repair_made = False
                gen2 = None
                eval2 = None

                # Repair phase (1 repair allowed if rejected by detector)
                if not first_accepted and gen1["text"]:
                    repair_msgs = build_repair_message(msgs, gen1["text"], eval1.get("diagnostics", ""))
                    repair_wait = max(0.0, args.interval - (time.monotonic() - last_req_time))
                    if repair_wait > 0:
                        await asyncio.sleep(repair_wait)

                    last_req_time = time.monotonic()
                    gen2 = await client.generate(repair_msgs, model)
                    if gen2["status_code"] == 429:
                        await asyncio.sleep(60.0)
                        gen2 = await client.generate(repair_msgs, model)

                    eval2 = evaluate_attempt(gen2["text"], arm, case, contract, engine)
                    final_accepted = eval2["accepted"]
                    final_correct = eval2["oracleCorrect"]
                    repair_made = True

                # False acceptance: detector accepted, but oracle says it was wrong!
                false_acceptance = bool(final_accepted and not final_correct)

                tot_inp = gen1.get("input_tokens", 0) + (gen2.get("input_tokens", 0) if gen2 else 0)
                tot_out = gen1.get("output_tokens", 0) + (gen2.get("output_tokens", 0) if gen2 else 0)

                record = {
                    "caseId": slot["caseId"],
                    "project": case["project"],
                    "family": case["family"],
                    "model": model,
                    "repeat": repeat,
                    "arm": arm,
                    "worker": worker_id,
                    "firstAccepted": first_accepted,
                    "firstCorrect": first_correct,
                    "finalAccepted": final_accepted,
                    "finalCorrect": final_correct,
                    "falseAcceptance": false_acceptance,
                    "repairAttempted": repair_made,
                    "totalInputTokens": tot_inp,
                    "totalOutputTokens": tot_out,
                    "latency1Ms": gen1.get("latency_ms"),
                    "latency2Ms": gen2.get("latency_ms") if gen2 else None,
                    "rawResponse1": gen1.get("text"),
                    "rawResponse2": gen2.get("text") if gen2 else None,
                    "recordedAt": datetime.now(timezone.utc).isoformat()
                }

                async with lock:
                    all_rows.append(record)
                    with runs_path.open("a", encoding="utf-8") as rf:
                        rf.write(json.dumps(record, ensure_ascii=False) + "\n")
                    
                    done_count = len(all_rows)
                    if done_count % 5 == 0 or done_count == len(slots):
                        summ = compute_summary(all_rows, len(slots))
                        summary_path.write_text(json.dumps(summ, indent=2) + "\n", encoding="utf-8")
                        pct = summ["completionPct"]
                        print(f"[{done_count}/{len(slots)} - {pct}%] W{worker_id}: {slot['caseId']} ({case['project'][:10]}) | {model.split('/')[-1]} | Arm {arm} -> Final: {'PASS' if final_correct else 'FAIL'}")

                queue.task_done()
        finally:
            await client.close()

    keys = get_groq_keys()
    tasks = [asyncio.create_task(worker(i, k)) for i, k in enumerate(keys)]
    await asyncio.gather(*tasks)

    # Final summary update
    final_summ = compute_summary(all_rows, len(slots))
    summary_path.write_text(json.dumps(final_summ, indent=2) + "\n", encoding="utf-8")
    print("\n=== Experiment Execution Completed! ===")
    print(f"Total completed: {len(all_rows)} slots.")
    print("Summary by Arm:")
    for arm, d in final_summ["byArm"].items():
        print(f"  Arm {arm}: {d.get('finalCorrect')}/{d.get('slots')} ({d.get('finalCorrectPct')}%) | False Acceptances: {d.get('falseAcceptance')} ({d.get('falseAcceptancePct')}%) | Mean Tokens: {d.get('meanInputTokens')} in / {d.get('meanOutputTokens')} out")


if __name__ == "__main__":
    asyncio.run(main())
