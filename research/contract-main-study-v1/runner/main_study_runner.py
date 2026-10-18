"""Main study runner adapter for HESchema controlled benchmark.

Executes reproducible comparisons between ordinary JSON Schema (Arm A)
and HESchema contracts with approved context (Arm B), plus optional controls C/D.
"""

import argparse
import asyncio
import copy
import hashlib
import json
import os
import pathlib
import random
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from heschema.contracts import Contract
from heschema.context_schema import effective_schema

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

try:
    from .strict_parser import StrictParseError, parse_strict_json, json_semantic_equal
    from .oracle import CorrectnessOracle, reconstruct_reference_output
    from .prompt_builder import build_generation_messages, build_repair_messages
    from .detector import detect_acceptance, DetectionResult
    from .failure_classifier import classify_failure
except ImportError:
    from strict_parser import StrictParseError, parse_strict_json, json_semantic_equal
    from oracle import CorrectnessOracle, reconstruct_reference_output
    from prompt_builder import build_generation_messages, build_repair_messages
    from detector import detect_acceptance, DetectionResult
    from failure_classifier import classify_failure

BASE_DIR = ROOT / "research" / "contract-main-study-v1"
INPUTS_DIR = BASE_DIR / "inputs"
EVAL_DIR = BASE_DIR / "evaluation"
RUNS_DIR = BASE_DIR / "runs"


class ProviderClient:
    """HTTP client managing API calls, pacing, retries, and key rotation."""

    def __init__(self, keys: List[str], base_url: str = "https://api.groq.com/openai/v1", mock: bool = False):
        self.keys = [k for k in keys if k]
        self.base_url = base_url.rstrip("/")
        self.mock = mock
        self.current_key_idx = 0
        self.client = None if mock else httpx.Client(timeout=60.0)
        self.last_request_time = 0.0

    def get_headers(self) -> Dict[str, str]:
        key = self.keys[self.current_key_idx] if self.keys else ""
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }

    def rotate_key(self):
        if len(self.keys) > 1:
            self.current_key_idx = (self.current_key_idx + 1) % len(self.keys)

    def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        min_interval_s: float = 1.0
    ) -> Dict[str, Any]:
        """Sends request to model endpoint with pacing and usage logging."""
        if self.mock:
            # Deterministic mock response for offline dry-run testing
            time.sleep(0.01)
            return {
                "text": json.dumps({"status": "mock_output"}),
                "raw": {},
                "input_tokens": 100,
                "output_tokens": 50,
                "reasoning_tokens": 0,
                "latency_ms": 10.0,
                "wait_ms": 0.0,
                "request_id": "mock-req-001",
                "error": None
            }

        # Pacing
        now = time.time()
        elapsed = now - self.last_request_time
        wait_ms = 0.0
        if elapsed < min_interval_s:
            wait_s = min_interval_s - elapsed
            wait_ms = wait_s * 1000.0
            time.sleep(wait_s)

        headers = self.get_headers()
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        start_t = time.perf_counter()
        retries = 0
        max_retries = max(8, len(self.keys) * 3)

        while retries <= max_retries:
            try:
                resp = self.client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                self.last_request_time = time.time()
                latency_ms = (time.perf_counter() - start_t) * 1000.0

                if resp.status_code == 200:
                    data = resp.json()
                    choice = data["choices"][0]
                    text = choice["message"].get("content", "")
                    usage = data.get("usage", {})
                    req_id = resp.headers.get("x-request-id", data.get("id", "unknown"))

                    # Check token limits to proactively avoid 429
                    rem_tokens = resp.headers.get("x-ratelimit-remaining-tokens")
                    if rem_tokens is not None:
                        try:
                            if int(rem_tokens) < 1500:
                                time.sleep(1.5)
                        except Exception:
                            pass

                    # Rotate key on successful request to balance quota
                    self.rotate_key()

                    return {
                        "text": text,
                        "raw": data,
                        "input_tokens": usage.get("prompt_tokens"),
                        "output_tokens": usage.get("completion_tokens"),
                        "reasoning_tokens": usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0),
                        "latency_ms": latency_ms,
                        "wait_ms": wait_ms,
                        "request_id": req_id,
                        "error": None
                    }

                elif resp.status_code == 429:
                    # Rate limited: parse retry-after from header or error body
                    wait_time = 5.0
                    header_wait = resp.headers.get("retry-after")
                    if header_wait:
                        try:
                            wait_time = float(header_wait)
                        except Exception:
                            pass
                    else:
                        import re
                        m = re.search(r"try again in (?:(\d+)m)?([\d\.]+)s", resp.text)
                        if m:
                            mins = float(m.group(1)) if m.group(1) else 0.0
                            secs = float(m.group(2))
                            wait_time = mins * 60.0 + secs + 1.0

                    wait_time = min(wait_time, 30.0)

                    print(f"  [429 Rate Limit] Key {self.current_key_idx+1} rate-limited for {model}. Rotating key.")
                    self.rotate_key()
                    headers = self.get_headers()
                    retries += 1
                    if retries >= len(self.keys):
                        # All available keys currently rate-limited for this model
                        return {
                            "text": None,
                            "raw": {"status_code": 429, "body": resp.text[:200]},
                            "input_tokens": None,
                            "output_tokens": None,
                            "reasoning_tokens": None,
                            "latency_ms": latency_ms,
                            "wait_ms": wait_ms,
                            "request_id": "error",
                            "error": "rate_limited_cooldown",
                            "cooldown_s": wait_time
                        }
                    time.sleep(0.5)
                else:
                    return {
                        "text": None,
                        "raw": {"status_code": resp.status_code, "body": resp.text[:500]},
                        "input_tokens": None,
                        "output_tokens": None,
                        "reasoning_tokens": None,
                        "latency_ms": latency_ms,
                        "wait_ms": wait_ms,
                        "request_id": "error",
                        "error": f"HTTP {resp.status_code}: {resp.text[:200]}"
                    }

            except Exception as exc:
                latency_ms = (time.perf_counter() - start_t) * 1000.0
                time.sleep(1.0)
                retries += 1
                if retries > max_retries:
                    return {
                        "text": None,
                        "raw": {"exception": str(exc)},
                        "input_tokens": None,
                        "output_tokens": None,
                        "reasoning_tokens": None,
                        "latency_ms": latency_ms,
                        "wait_ms": wait_ms,
                        "request_id": "error",
                        "error": f"Network exception: {exc}"
                    }

        return {
            "text": None,
            "raw": {},
            "input_tokens": None,
            "output_tokens": None,
            "reasoning_tokens": None,
            "latency_ms": 0.0,
            "wait_ms": wait_ms,
            "request_id": "error",
            "error": "Exceeded maximum transport retries"
        }

    def close(self):
        if self.client:
            self.client.close()


def generate_schedule(
    cases: List[Dict[str, Any]],
    models: List[str],
    repeats: int,
    arms: List[str],
    seed: int = 20261017
) -> List[Dict[str, Any]]:
    """Builds a deterministic execution schedule with shuffled tuple order and paired arms."""
    rng = random.Random(seed)

    # 1. Generate (case, model, repeat) tuples
    tuples = []
    for c in cases:
        for m in models:
            for r in range(1, repeats + 1):
                tuples.append((c['id'], m, r))

    # 2. Shuffle tuples once
    rng.shuffle(tuples)

    # 3. For each tuple, randomize arm order
    schedule = []
    order_idx = 0
    for cid, mid, rep in tuples:
        arm_order = list(arms)
        rng.shuffle(arm_order)
        for arm in arm_order:
            schedule.append({
                "order": order_idx,
                "case_id": cid,
                "model_id": mid,
                "repeat": rep,
                "arm": arm,
                "slot_key": f"{cid}_{mid}_{rep}_{arm}"
            })
            order_idx += 1

    return schedule


def run_experiment(
    cases_file: pathlib.Path,
    gold_file: pathlib.Path,
    run_dir: pathlib.Path,
    models: List[str],
    repeats: int,
    arms: List[str],
    keys: List[str],
    mock: bool = False,
    cases_limit: Optional[int] = None,
    seed: int = 20261017,
    pacing_s: float = 1.0,
    workers: int = 3
):
    """Executes the full controlled experiment run with append-only logging and parallel workers."""
    run_dir.mkdir(parents=True, exist_ok=True)
    cases = json.loads(cases_file.read_text(encoding="utf-8"))
    if cases_limit is not None and cases_limit > 0:
        cases = cases[:cases_limit]

    gold_rows = [json.loads(line) for line in gold_file.read_text(encoding="utf-8").splitlines()]
    gold_by_id = {r['id']: r['expected_output'] for r in gold_rows}
    case_by_id = {c['id']: c for c in cases}

    oracle = CorrectnessOracle(gold_by_id)

    # Generate or load schedule
    schedule_file = run_dir / "schedule.json"
    if schedule_file.exists():
        schedule = json.loads(schedule_file.read_text(encoding="utf-8"))
    else:
        schedule = generate_schedule(cases, models, repeats, arms, seed=seed)
        schedule_file.write_text(json.dumps(schedule, indent=2), encoding="utf-8")

    # Load existing checkpoints
    checkpoints_file = run_dir / "checkpoints.json"
    checkpoints = {"completed": {}}
    if checkpoints_file.exists():
        try:
            checkpoints = json.loads(checkpoints_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    requests_file = run_dir / "requests.jsonl"
    responses_file = run_dir / "responses.jsonl"
    attempts_file = run_dir / "attempts.jsonl"
    judgments_file = run_dir / "judgments.jsonl"

    total_slots = len(schedule)
    completed_slots = set(checkpoints["completed"].keys())
    print(f"Starting run {run_dir.name}: {total_slots} slots total, {len(completed_slots)} already completed.")

    req_f = open(requests_file, "a", encoding="utf-8")
    resp_f = open(responses_file, "a", encoding="utf-8")
    att_f = open(attempts_file, "a", encoding="utf-8")
    judg_f = open(judgments_file, "a", encoding="utf-8")

    file_lock = threading.Lock()
    active_slots = set()
    all_done = threading.Event()

    actual_workers = max(1, min(workers, len(keys) if keys else 1))
    print(f"Executing study with {actual_workers} parallel worker(s) across {len(keys)} API keys.")

    providers = []
    for wid in range(actual_workers):
        p = ProviderClient(keys=keys, mock=mock)
        p.current_key_idx = (wid * 2) % len(keys) if keys else 0
        providers.append(p)

    def worker_loop(wid: int, provider: ProviderClient):
        worker_cooldowns: Dict[str, float] = {}
        while len(completed_slots) < total_slots and not all_done.is_set():
            target_item = None
            now = time.time()
            with file_lock:
                for item in schedule:
                    sk = item["slot_key"]
                    if sk in completed_slots or sk in active_slots:
                        continue
                    m = item["model_id"]
                    if m in worker_cooldowns and now < worker_cooldowns[m]:
                        continue
                    target_item = item
                    active_slots.add(sk)
                    break

            if target_item is None:
                if len(completed_slots) >= total_slots:
                    break
                future_cds = [cd - time.time() for cd in worker_cooldowns.values() if cd > time.time()]
                sleep_s = min(future_cds) if future_cds else 2.0
                sleep_s = max(1.0, min(sleep_s, 10.0))
                time.sleep(sleep_s)
                continue

            slot_key = target_item["slot_key"]
            cid = target_item["case_id"]
            repeat = target_item["repeat"]
            arm = target_item["arm"]
            model = target_item["model_id"]
            case = case_by_id[cid]

            print(f"[W{wid+1}][{len(completed_slots)+1}/{total_slots}] Slot {slot_key} (Case: {cid}, Model: {model}, Arm: {arm}, Rep: {repeat})")

            # --- STEP 1: INITIAL GENERATION ---
            init_messages = build_generation_messages(case, arm)
            req_record_init = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "slot_key": slot_key,
                "type": "initial",
                "model": model,
                "arm": arm,
                "messages": init_messages
            }
            with file_lock:
                req_f.write(json.dumps(req_record_init, ensure_ascii=False) + "\n")
                req_f.flush()

            init_gen = provider.generate(init_messages, model=model, min_interval_s=pacing_s)
            if init_gen.get("error") == "rate_limited_cooldown":
                cooldown_s = min(init_gen.get("cooldown_s", 30.0), 30.0)
                worker_cooldowns[model] = time.time() + cooldown_s
                print(f"  [W{wid+1} Model Cooldown] Keys rate-limited for {model}. Cooling down for {cooldown_s:.1f}s. Moving to next slot.")
                with file_lock:
                    active_slots.discard(slot_key)
                continue

            resp_record_init = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "slot_key": slot_key,
                "type": "initial",
                "model": model,
                "arm": arm,
                "generation": init_gen
            }
            with file_lock:
                resp_f.write(json.dumps(resp_record_init, ensure_ascii=False) + "\n")
                resp_f.flush()

            init_text = init_gen.get("text")
            init_error = init_gen.get("error")

            # Detection on initial
            init_detection = detect_acceptance(case, init_text or "", arm)
            # Oracle on initial
            init_correct, init_parsed, init_oracle_err = oracle.score_response(case, init_text or "")
            init_failures = classify_failure(case, init_text, init_detection, init_correct, transport_error=init_error)

            # --- STEP 2: REPAIR (IF REJECTED BY DETECTOR) ---
            repair_needed = bool(not init_detection.accepted and init_text is not None and not init_error)
            repair_attempted = False
            repair_gen = None
            repair_detection = None
            repair_correct = None
            final_failures = list(init_failures)

            if repair_needed:
                repair_attempted = True
                diag_msg = init_detection.diagnostic_summary()
                repair_messages = build_repair_messages(init_messages, init_text, diag_msg)

                req_record_rep = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "slot_key": slot_key,
                    "type": "repair",
                    "model": model,
                    "arm": arm,
                    "messages": repair_messages
                }
                with file_lock:
                    req_f.write(json.dumps(req_record_rep, ensure_ascii=False) + "\n")
                    req_f.flush()

                repair_gen = provider.generate(repair_messages, model=model, min_interval_s=pacing_s)
                if repair_gen.get("error") == "rate_limited_cooldown":
                    cooldown_s = min(repair_gen.get("cooldown_s", 30.0), 30.0)
                    worker_cooldowns[model] = time.time() + cooldown_s
                    print(f"  [W{wid+1} Model Cooldown] Keys rate-limited for {model} during repair. Recording failure.")

                resp_record_rep = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "slot_key": slot_key,
                    "type": "repair",
                    "model": model,
                    "arm": arm,
                    "generation": repair_gen
                }
                with file_lock:
                    resp_f.write(json.dumps(resp_record_rep, ensure_ascii=False) + "\n")
                    resp_f.flush()

                rep_text = repair_gen.get("text")
                rep_err = repair_gen.get("error")
                repair_detection = detect_acceptance(case, rep_text or "", arm)
                repair_correct, rep_parsed, _ = oracle.score_response(case, rep_text or "")
                final_failures = classify_failure(case, rep_text, repair_detection, repair_correct, transport_error=rep_err)

            # Determine final status
            final_accepted = repair_detection.accepted if repair_attempted and repair_detection else init_detection.accepted
            final_correct = repair_correct if repair_attempted and repair_correct is not None else init_correct

            attempt_record = {
                "order": target_item["order"],
                "slot_key": slot_key,
                "case_id": cid,
                "source_group": case.get("source_group", ""),
                "task_family": case.get("task_family", ""),
                "model_id": model,
                "repeat": repeat,
                "arm": arm,
                "first_pass": {
                    "accepted": init_detection.accepted,
                    "correct": init_correct,
                    "failure_labels": init_failures,
                    "input_tokens": init_gen.get("input_tokens"),
                    "output_tokens": init_gen.get("output_tokens"),
                    "reasoning_tokens": init_gen.get("reasoning_tokens"),
                    "latency_ms": init_gen.get("latency_ms"),
                    "wait_ms": init_gen.get("wait_ms"),
                    "error": init_error
                },
                "repair": {
                    "attempted": repair_attempted,
                    "accepted": repair_detection.accepted if repair_detection else None,
                    "correct": repair_correct,
                    "input_tokens": repair_gen.get("input_tokens") if repair_gen else None,
                    "output_tokens": repair_gen.get("output_tokens") if repair_gen else None,
                    "reasoning_tokens": repair_gen.get("reasoning_tokens") if repair_gen else None,
                    "latency_ms": repair_gen.get("latency_ms") if repair_gen else None,
                    "wait_ms": repair_gen.get("wait_ms") if repair_gen else None,
                    "error": repair_gen.get("error") if repair_gen else None
                },
                "final": {
                    "accepted": final_accepted,
                    "correct": final_correct,
                    "failure_labels": final_failures,
                    "total_input_tokens": (init_gen.get("input_tokens") or 0) + ((repair_gen.get("input_tokens") or 0) if repair_gen else 0),
                    "total_output_tokens": (init_gen.get("output_tokens") or 0) + ((repair_gen.get("output_tokens") or 0) if repair_gen else 0),
                    "total_latency_ms": (init_gen.get("latency_ms") or 0) + ((repair_gen.get("latency_ms") or 0) if repair_gen else 0),
                    "total_wait_ms": (init_gen.get("wait_ms") or 0) + ((repair_gen.get("wait_ms") or 0) if repair_gen else 0),
                }
            }

            judgment_record = {
                "order": target_item["order"],
                "slot_key": slot_key,
                "case_id": cid,
                "model_id": model,
                "arm": arm,
                "repeat": repeat,
                "first_pass_accepted": init_detection.accepted,
                "first_pass_correct": init_correct,
                "repair_attempted": repair_attempted,
                "repair_accepted": repair_detection.accepted if repair_detection else None,
                "repair_correct": repair_correct,
                "final_accepted": final_accepted,
                "final_correct": final_correct,
                "false_acceptance": bool(final_accepted and not final_correct),
                "false_rejection": bool(not init_detection.accepted and init_correct),
                "failure_labels": final_failures
            }

            with file_lock:
                att_f.write(json.dumps(attempt_record, ensure_ascii=False) + "\n")
                att_f.flush()
                judg_f.write(json.dumps(judgment_record, ensure_ascii=False) + "\n")
                judg_f.flush()
                checkpoints["completed"][slot_key] = {
                    "first_pass_correct": init_correct,
                    "final_correct": final_correct
                }
                completed_slots.add(slot_key)
                active_slots.discard(slot_key)
                checkpoints_file.write_text(json.dumps(checkpoints, indent=2), encoding="utf-8")

    threads = []
    try:
        for wid, prov in enumerate(providers):
            t = threading.Thread(target=worker_loop, args=(wid, prov), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()
    finally:
        all_done.set()
        req_f.close()
        resp_f.close()
        att_f.close()
        judg_f.close()
        for p in providers:
            p.close()

    print(f"Run completed. All {total_slots} attempts saved to {attempts_file}.")


def main():
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="HESchema Main Study Experiment Runner")
    parser.add_argument("--run-id", default=None, help="Identifier for run directory")
    parser.add_argument("--models", default="openai/gpt-oss-20b,openai/gpt-oss-120b,qwen/qwen3.8-27b", help="Comma-separated model IDs")
    parser.add_argument("--repeats", type=int, default=3, help="Repeats per case/model/arm")
    parser.add_argument("--arms", default="A,B", help="Comma-separated arms (A,B or A,B,C,D)")
    parser.add_argument("--cases-limit", type=int, default=None, help="Limit number of cases (e.g. for smoke test)")
    parser.add_argument("--mock", action="store_true", help="Run with mock provider (no external calls)")
    parser.add_argument("--pacing", type=float, default=1.0, help="Minimum pacing seconds between calls")
    parser.add_argument("--seed", type=int, default=20261017, help="Randomization seed")
    parser.add_argument("--workers", type=int, default=3, help="Number of parallel workers across keys")
    args = parser.parse_args()

    run_id = args.run_id or f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    run_dir = RUNS_DIR / run_id
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    arms = [a.strip().upper() for a in args.arms.split(",") if a.strip()]

    # Collect keys strictly from environment variables without exposing values
    keys = []
    primary_key = os.getenv("GROQ_API_KEY", "").strip()
    if primary_key:
        keys.append(primary_key)
    extra_keys = os.getenv("GROQ_API_KEYS", "").strip()
    if extra_keys:
        for k in extra_keys.split(","):
            k_clean = k.strip()
            if k_clean and k_clean not in keys:
                keys.append(k_clean)

    run_experiment(
        cases_file=INPUTS_DIR / "cases.json",
        gold_file=EVAL_DIR / "gold.private.jsonl",
        run_dir=run_dir,
        models=models,
        repeats=args.repeats,
        arms=arms,
        keys=keys,
        mock=args.mock,
        cases_limit=args.cases_limit,
        seed=args.seed,
        pacing_s=args.pacing,
        workers=args.workers
    )

if __name__ == "__main__":
    main()
