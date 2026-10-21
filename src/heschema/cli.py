"""Command-line entry points for experiments, runtime service and audit."""

import argparse
import asyncio
import json
import os
import time
from pathlib import Path

from .benchmark import run
from .dataset import audit, build, load_cases
from .domains import DOMAINS, reference_schema
from .experiments import dry_run, run_decoding, run_repair_study
from .jsonio import loads, read_json, write_json
from .metrics import compare_models
from .providers import ROOT, Provider, registry
from .reports import adapt_report
from .schema import SchemaEngine


def main():
    parser = argparse.ArgumentParser(prog="heschema")
    commands = parser.add_subparsers(dest="command", required=True)
    evidence = commands.add_parser('evidence-audit', help='Check saved study evidence without model calls')
    evidence.add_argument('path')
    research = commands.add_parser('research-audit', help='Audit prospective category cases without initializing providers')
    research.add_argument('--dataset', default=str(ROOT / 'research/relationship-categories-v1/cases.jsonl'))
    research.add_argument('--sources', default=str(ROOT / 'research/relationship-categories-v1/sources.json'))
    research.add_argument('--out')
    research.add_argument('--engine', choices=['jsonschema', 'blaze'], default='jsonschema')
    categories = commands.add_parser('category-report', help='Describe category outcomes across compatible saved reports')
    categories.add_argument('reports', nargs='+')
    categories.add_argument('--out')
    commands.add_parser("providers")
    dataset = commands.add_parser("dataset")
    dataset.add_argument("--build", action="store_true")
    dataset.add_argument("--path", default=str(ROOT / "benchmarks/cases.jsonl"))
    bench = commands.add_parser("benchmark")
    bench.add_argument("--dataset", default=str(ROOT / "benchmarks/cases.jsonl"))
    bench.add_argument("--provider", default="mock", choices=list(registry()))
    bench.add_argument("--model")
    bench.add_argument("--domain")
    bench.add_argument("--schema")
    bench.add_argument("--minimal-schema")
    bench.add_argument("--out", default="results/run")
    bench.add_argument("--repeats", type=int, default=3)
    bench.add_argument("--repairs", type=int, default=2)
    bench.add_argument("--feedback-style", choices=["generic", "raw", "actionable"], default="actionable")
    bench.add_argument("--seed", type=int, default=42)
    bench.add_argument("--limit", type=int)
    bench.add_argument("--max-requests", type=int)
    bench.add_argument("--max-tokens", type=int, default=1024)
    bench.add_argument("--temperature", type=float)
    bench.add_argument("--interval", type=float)
    bench.add_argument("--engine", choices=["jsonschema", "blaze"], default="jsonschema")
    bench.add_argument("--input-price", type=float, help="USD per million input tokens")
    bench.add_argument("--output-price", type=float, help="USD per million output tokens")
    decoding = commands.add_parser("decoding-study")
    decoding.add_argument("--dataset", default=str(ROOT / "benchmarks/heldout.jsonl"))
    decoding.add_argument("--provider", default="mock", choices=list(registry()))
    decoding.add_argument("--model")
    decoding.add_argument("--out", default="results/decoding")
    decoding.add_argument("--execute", action="store_true", help="Default is a request-count dry run")
    decoding.add_argument("--repeats", type=int, default=1)
    decoding.add_argument("--max-requests", type=int)
    decoding.add_argument("--max-tokens", type=int, default=1024)
    decoding.add_argument("--seed", type=int, default=42)
    decoding.add_argument("--warmup", type=int, default=0)
    decoding.add_argument('--engine', choices=['jsonschema', 'blaze'], default='jsonschema')
    decoding.add_argument("--modes", nargs="+", choices=["prompt_only", "native_original", "native_projected"], default=["prompt_only", "native_original", "native_projected"])
    recovery = commands.add_parser("repair-study")
    recovery.add_argument("--dataset", default=str(ROOT / "benchmarks/heldout.jsonl"))
    recovery.add_argument("--first-out", required=True)
    recovery.add_argument("--out", default="results/repair-feedback")
    recovery.add_argument("--provider", default="mock", choices=list(registry()))
    recovery.add_argument("--model")
    recovery.add_argument("--execute", action="store_true")
    recovery.add_argument("--budgets", type=int, nargs="+", default=[1, 2])
    recovery.add_argument("--styles", nargs="+", choices=["generic", "raw", "actionable"], default=["generic", "raw", "actionable"])
    recovery.add_argument("--max-requests", type=int)
    adapter = commands.add_parser("report")
    adapter.add_argument("path")
    compare = commands.add_parser("compare-models")
    compare.add_argument("reports", nargs=2, help="Small model report, then large model report")
    speed = commands.add_parser("speed")
    speed.add_argument("--engine", choices=["jsonschema", "blaze"], default="jsonschema")
    speed.add_argument("--iterations", type=int, default=10000)
    speed.add_argument("--out", default="results/speed.json")
    serve = commands.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()
    if args.command == 'evidence-audit':
        from .study_evidence import StudyEvidence
        report = StudyEvidence(args.path).audit()
        print(json.dumps(report, indent=2))
        if not report['evidenceComplete'] or report.get('scheduleComplete') is False:
            raise SystemExit(1)
    elif args.command == 'research-audit':
        from .research_cases import audit_cases
        report = audit_cases(args.dataset, args.sources, backend=args.engine)
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({k: v for k, v in report.items() if k != 'probes'}, indent=2))
        if not report['passed']:
            raise SystemExit(1)
    elif args.command == 'category-report':
        from .category_reports import category_report
        report = category_report(args.reports)
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report, indent=2))
    elif args.command == "providers":
        print(json.dumps(registry(), indent=2))
    elif args.command == "dataset":
        if args.build:
            build(Path(args.path).parent)
        print(json.dumps(audit(load_cases(args.path)), indent=2))
    elif args.command == "compare-models":
        print(json.dumps(compare_models([read_json(p) for p in args.reports]), indent=2))
    elif args.command == "report":
        print(json.dumps(adapt_report(read_json(args.path)), indent=2))
    elif args.command in {"decoding-study", "repair-study"}:
        cases = [loads(line) for line in Path(args.dataset).read_text(encoding="utf-8").splitlines() if line.strip()]
        if args.command == "decoding-study":
            estimate = dry_run(cases, args.repeats, args.modes, args.warmup)
        else:
            source = read_json(Path(args.first_out) / "config.json")
            estimate = dry_run(cases, source["repeats"], source["modes"], repair_budgets=args.budgets, feedback_styles=args.styles)
            estimate["alreadyRecordedFirstPassRequests"] = estimate["firstPassRequests"]
            estimate["maximumRequests"] = estimate["maximumRepairRequests"]
        if not args.execute:
            print(json.dumps(estimate, indent=2))
            return
        if args.provider != "mock" and args.max_requests is None:
            parser.error("Live execution requires --max-requests")
        async def controlled():
            provider = Provider(args.provider, args.model, interval=0 if args.provider == "mock" else None)
            try:
                if args.command == "decoding-study":
                    return await run_decoding(cases, provider, args.out, repeats=args.repeats, modes=args.modes,
                                              seed=args.seed, max_tokens=args.max_tokens, max_requests=args.max_requests, warmup=args.warmup, backend=args.engine)
                return await run_repair_study(cases, provider, args.first_out, args.out, budgets=args.budgets, styles=args.styles,
                                              max_tokens=source["maxTokens"], seed=source["seed"], temperature=source["temperature"], backend=source["engine"], max_requests=args.max_requests)
            finally:
                await provider.close()
        report = asyncio.run(controlled())
        print(json.dumps({"report": str(Path(args.out) / "report.json"), "complete": report["complete"], "empiricalLLMEvidence": report["empiricalLLMEvidence"]}, indent=2))
    elif args.command == "benchmark":
        cases = load_cases(args.dataset)
        if args.domain:
            cases = [c for c in cases if c["domain"] == args.domain]
        if args.limit is not None:
            if args.limit < 1:
                parser.error("--limit must be positive")
            cases = cases[:args.limit]
        if not cases:
            parser.error("No matching benchmark cases")

        async def experiment():
            provider = Provider(args.provider, args.model, args.interval)
            try:
                return await run(cases, provider, args.out,
                                 read_json(args.schema) if args.schema else None,
                                 read_json(args.minimal_schema) if args.minimal_schema else None,
                                 args.repeats, args.repairs, args.seed, args.max_tokens, args.temperature,
                                 args.engine, args.input_price, args.output_price, args.max_requests, feedback_style=args.feedback_style)
            finally:
                await provider.close()

        report = asyncio.run(experiment())
        print(json.dumps({"complete": report["complete"], "runs": report["completedRuns"],
                          "effects": report["effects"], "report": str(Path(args.out) / "report.md")}, indent=2))
    elif args.command == "speed":
        if args.iterations < 1:
            parser.error("Iterations must be positive")
        engine = SchemaEngine(args.engine)
        measurements = {}
        from .dataset import values
        try:
            for domain in DOMAINS:
                schema, instance = reference_schema(domain), values(domain, 0)
                start = time.perf_counter_ns()
                engine.register(schema)
                compile_ns = time.perf_counter_ns() - start
                for _ in range(100):
                    assert not engine.errors(schema, instance)
                start = time.perf_counter_ns()
                for _ in range(args.iterations):
                    engine.errors(schema, instance)
                measurements[domain] = {"registrationMs": compile_ns / 1e6,
                                        "meanValidationUs": (time.perf_counter_ns() - start) / args.iterations / 1000}
        finally:
            engine.close()
        report = {"engine": args.engine, "iterations": args.iterations, "domains": measurements,
                  "scope": "HESchema public validation path; includes IPC/reference checks when Blaze is enabled; not native Blaze kernel speed"}
        write_json(args.out, report)
        print(json.dumps(report, indent=2))
    else:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env", override=False)
        if args.host not in {"127.0.0.1", "localhost", "::1"} and not os.getenv("HESCHEMA_API_TOKEN"):
            parser.error("Set HESCHEMA_API_TOKEN before binding outside localhost")
        import uvicorn

        from .api import create_app
        uvicorn.run(create_app(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
