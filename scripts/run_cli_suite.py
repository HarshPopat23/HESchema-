"""Automated batch runner for the 10 CLI Integration pairs (C01 - C10).

Executes across all 4 operational modes:
1. Preview Request & Command (JSON payload, POSIX bash, PowerShell)
2. Run API Test (POST /v1/chat/completions loopback)
3. Run CLI Test (Backend Subprocess invoking Sourcemeta jsonschema llm)
4. Run Small Comparison (Both Modes: Native Schema vs. Prompt-Only Grounding)

Saves individual JSON logs and a consolidated summary report in results/cli_integration/.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from heschema.cli_integration import (
    CLI_PAIRS,
    evaluate_document_diagnostics,
    generate_command_previews,
)
from heschema.schema import SchemaEngine

RESULTS_DIR = ROOT / "results/cli_integration"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = os.getenv("HESCHEMA_BASE_URL", "http://127.0.0.1:8000")
MODEL = os.getenv("HESCHEMA_MODEL", "qwen3:4b-instruct")


async def run_pair(pair_id: str, pair_data: dict, client: httpx.AsyncClient, engine: SchemaEngine) -> dict:
    title = pair_data["title"]
    prompt = pair_data["prompt"]
    schema = pair_data["schema"]
    expected = pair_data.get("expected")
    notes = pair_data.get("notes", "")

    print(f"\n==================================================")
    print(f"Executing {pair_id}: {title}")
    print(f"==================================================")

    # ----------------------------------------------------
    # 1. Preview Request & Command
    # ----------------------------------------------------
    print("[1/4] Generating Command Previews...")
    previews = generate_command_previews(
        schema_path="schema.json",
        prompt=prompt,
        url=f"{BASE_URL}/v1/chat/completions",
        model=MODEL,
        mode="native_schema",
        max_tokens=1024,
        temperature=0.0,
        seed=42,
        has_token=False,
    )
    api_request_payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "schema", "strict": True, "schema": schema},
        },
        "stream": False,
        "max_tokens": 1024,
        "temperature": 0.0,
        "seed": 42,
        "heschema_mode": "native_schema",
    }

    # ----------------------------------------------------
    # 2. Run API Test (POST /v1/chat/completions)
    # ----------------------------------------------------
    print("[2/4] Running API Test (POST /v1/chat/completions)...")
    t0 = time.perf_counter()
    api_resp = await client.post(
        f"{BASE_URL}/v1/chat/completions",
        json=api_request_payload,
        timeout=180.0,
    )
    api_latency_ms = (time.perf_counter() - t0) * 1000

    api_result = {
        "status_code": api_resp.status_code,
        "latency_ms": round(api_latency_ms, 2),
    }

    raw_content = ""
    parsed_json = None
    diag = {}
    if api_resp.status_code == 200:
        api_data = api_resp.json()
        api_result["response"] = api_data
        raw_content = api_data["choices"][0]["message"]["content"]
        finish_reason = api_data["choices"][0].get("finish_reason")
        usage = api_data.get("usage", {})
        api_result["content"] = raw_content
        api_result["finish_reason"] = finish_reason
        api_result["usage"] = usage

        # Evaluate diagnostics
        diag = evaluate_document_diagnostics(schema, raw_content, engine)
        api_result["diagnostics"] = diag
        try:
            parsed_json = json.loads(raw_content)
        except Exception:
            parsed_json = None
        print(f"  -> HTTP 200 | Latency: {api_latency_ms:.0f}ms | Schema Valid: {diag.get('heschemaSchemaValid')}")
    else:
        api_result["error"] = api_resp.text
        print(f"  -> HTTP {api_resp.status_code}: {api_resp.text[:200]}")

    # ----------------------------------------------------
    # 3. Run CLI Test (Backend Subprocess)
    # ----------------------------------------------------
    print("[3/4] Running CLI Test (Sourcemeta Subprocess)...")
    cli_payload = {
        "schema": schema,
        "prompt": prompt,
        "model": MODEL,
        "mode": "native_schema",
        "maxTokens": 1024,
        "temperature": 0.0,
        "seed": 42,
        "timeout": 180.0,
    }
    t0 = time.perf_counter()
    cli_resp = await client.post(
        f"{BASE_URL}/ui/cli-integration/run",
        json=cli_payload,
        timeout=180.0,
    )
    cli_backend_elapsed_ms = (time.perf_counter() - t0) * 1000

    cli_result = {
        "status_code": cli_resp.status_code,
        "backend_elapsed_ms": round(cli_backend_elapsed_ms, 2),
    }
    if cli_resp.status_code == 200:
        cli_data = cli_resp.json()
        cli_result.update(cli_data)
        print(f"  -> Exit: {cli_data.get('exitCode')} | CLI Success: {cli_data.get('cliRunSuccess')} | Elapsed: {cli_data.get('elapsedMs', 0):.0f}ms")
    else:
        cli_result["error"] = cli_resp.text
        print(f"  -> HTTP {cli_resp.status_code}: {cli_resp.text[:200]}")

    # ----------------------------------------------------
    # 4. Run Small Comparison (Both Modes)
    # ----------------------------------------------------
    print("[4/4] Running Comparison (Native Schema vs. Prompt-Only)...")
    # Trial 1: Native Schema
    payload_native = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "schema", "strict": True, "schema": schema},
        },
        "stream": False,
        "max_tokens": 1024,
        "temperature": 0.0,
        "seed": 42,
        "heschema_mode": "native_schema",
    }
    t0 = time.perf_counter()
    resp_nat = await client.post(f"{BASE_URL}/v1/chat/completions", json=payload_native, timeout=180.0)
    lat_nat = (time.perf_counter() - t0) * 1000
    nat_data = resp_nat.json() if resp_nat.status_code == 200 else {}
    nat_content = nat_data.get("choices", [{}])[0].get("message", {}).get("content", "")
    nat_diag = evaluate_document_diagnostics(schema, nat_content, engine) if nat_content else {"heschemaSchemaValid": False}

    # Trial 2: Prompt-Only Grounding
    payload_prompt = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "schema", "strict": False, "schema": schema},
        },
        "stream": False,
        "max_tokens": 1024,
        "temperature": 0.0,
        "seed": 42,
        "heschema_mode": "prompt_only",
    }
    t0 = time.perf_counter()
    resp_prompt = await client.post(f"{BASE_URL}/v1/chat/completions", json=payload_prompt, timeout=180.0)
    lat_prompt = (time.perf_counter() - t0) * 1000
    prompt_data = resp_prompt.json() if resp_prompt.status_code == 200 else {}
    prompt_content = prompt_data.get("choices", [{}])[0].get("message", {}).get("content", "")
    prompt_diag = evaluate_document_diagnostics(schema, prompt_content, engine) if prompt_content else {"heschemaSchemaValid": False}

    comparison_result = {
        "native_schema": {
            "status_code": resp_nat.status_code,
            "latency_ms": round(lat_nat, 2),
            "tokens": nat_data.get("usage", {}).get("total_tokens"),
            "completion_tokens": nat_data.get("usage", {}).get("completion_tokens"),
            "schema_valid": nat_diag.get("heschemaSchemaValid", False),
            "content": nat_content,
        },
        "prompt_only": {
            "status_code": resp_prompt.status_code,
            "latency_ms": round(lat_prompt, 2),
            "tokens": prompt_data.get("usage", {}).get("total_tokens"),
            "completion_tokens": prompt_data.get("usage", {}).get("completion_tokens"),
            "schema_valid": prompt_diag.get("heschemaSchemaValid", False),
            "content": prompt_content,
        },
    }
    print(f"  -> Native Valid: {nat_diag.get('heschemaSchemaValid')} ({lat_nat:.0f}ms) vs Prompt-Only Valid: {prompt_diag.get('heschemaSchemaValid')} ({lat_prompt:.0f}ms)")

    # Consolidate record
    pair_record = {
        "id": pair_id,
        "title": title,
        "notes": notes,
        "prompt": prompt,
        "schema": schema,
        "expected": expected,
        "previews": {
            "api_request": api_request_payload,
            "posix": previews["posix"],
            "powershell": previews["powershell"],
        },
        "api_test": api_result,
        "cli_test": cli_result,
        "comparison": comparison_result,
    }

    # Save individual artifact
    safe_slug = title.split(".")[1].strip().lower().replace(" ", "_").replace(":", "").replace("/", "_").replace("$", "")
    artifact_path = RESULTS_DIR / f"{pair_id}_{safe_slug}.json"
    artifact_path.write_text(json.dumps(pair_record, indent=2), encoding="utf-8")
    print(f"Saved: {artifact_path.name}")

    return pair_record


async def main():
    print(f"Connecting to HESchema backend at {BASE_URL}...")
    async with httpx.AsyncClient() as client:
        # Check health
        try:
            h = await client.get(f"{BASE_URL}/health", timeout=10.0)
            if h.status_code != 200:
                print(f"Backend health check returned {h.status_code}")
                sys.exit(1)
        except Exception as e:
            print(f"Failed to connect to {BASE_URL}: {e}")
            sys.exit(1)

        engine = SchemaEngine("jsonschema")
        records = []
        try:
            pair_keys = [f"C{i:02d}" for i in range(1, 11)]
            for p_id in pair_keys:
                if p_id in CLI_PAIRS:
                    rec = await run_pair(p_id, CLI_PAIRS[p_id], client, engine)
                    records.append(rec)
        finally:
            engine.close()

    # Generate summary JSON
    summary_path = RESULTS_DIR / "summary.json"
    summary_path.write_text(json.dumps({"model": MODEL, "pairs": records}, indent=2), encoding="utf-8")
    print(f"\nConsolidated JSON written to {summary_path}")

    # Generate summary Markdown Table
    md_lines = [
        "# CLI Integration Test Suite: 10 Canonical Pairs Report",
        "",
        f"- **Model**: `{MODEL}`",
        f"- **Backend Loopback**: `{BASE_URL}/v1/chat/completions`",
        f"- **Date / Time**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Summary Results Table",
        "",
        "| ID | Test Scenario | API Valid | API Latency | CLI Exit | CLI Elapsed | Native Valid | Prompt-Only Valid | Conformance Difference |",
        "|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|",
    ]

    for r in records:
        pid = r["id"]
        title_short = r["title"].split(".")[1].strip()
        api_valid = "✅ PASS" if r["api_test"].get("diagnostics", {}).get("heschemaSchemaValid") else "❌ FAIL"
        api_lat = f"{r['api_test'].get('latency_ms', 0):.0f} ms"
        cli_exit = f"Code {r['cli_test'].get('exitCode', -1)}"
        cli_time = f"{r['cli_test'].get('elapsedMs', 0):.0f} ms"

        cmp = r["comparison"]
        nat_valid = "✅ PASS" if cmp["native_schema"]["schema_valid"] else "❌ FAIL"
        prompt_valid = "✅ PASS" if cmp["prompt_only"]["schema_valid"] else "❌ FAIL"

        if cmp["native_schema"]["schema_valid"] and not cmp["prompt_only"]["schema_valid"]:
            diff = "**Native Prevents Violation**"
        elif cmp["native_schema"]["schema_valid"] and cmp["prompt_only"]["schema_valid"]:
            diff = "Both Passed"
        else:
            diff = "Constrained Review"

        md_lines.append(
            f"| **{pid}** | {title_short} | {api_valid} | {api_lat} | {cli_exit} | {cli_time} | {nat_valid} | {prompt_valid} | {diff} |"
        )

    md_lines.extend([
        "",
        "## Detailed Observations per Pair",
        "",
    ])

    for r in records:
        pid = r["id"]
        md_lines.append(f"### {r['title']}")
        md_lines.append(f"- **Focus**: {r['notes']}")
        md_lines.append(f"- **API Test Output**:")
        md_lines.append("```json")
        md_lines.append(r["api_test"].get("content", "(No output)"))
        md_lines.append("```")
        if r["cli_test"].get("parsedJson"):
            md_lines.append(f"- **Sourcemeta CLI Result**: Exit Code `{r['cli_test'].get('exitCode')}`")
        md_lines.append("")

    summary_md_path = RESULTS_DIR / "summary.md"
    summary_md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Consolidated Markdown report written to {summary_md_path}")
    print("\nSuite execution completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
