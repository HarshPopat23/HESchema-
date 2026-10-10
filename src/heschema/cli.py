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
from .jsonio import read_json, write_json
from .metrics import compare_models
from .providers import ROOT, Provider, registry
from .schema import SchemaEngine


def main():
    parser = argparse.ArgumentParser(prog="heschema")
    commands = parser.add_subparsers(dest="command", required=True)
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
    bench.add_argument("--seed", type=int, default=42)
    bench.add_argument("--limit", type=int)
    bench.add_argument("--max-requests", type=int)
    bench.add_argument("--max-tokens", type=int, default=1024)
    bench.add_argument("--temperature", type=float)
    bench.add_argument("--interval", type=float)
    bench.add_argument("--engine", choices=["jsonschema", "blaze"], default="jsonschema")
    bench.add_argument("--input-price", type=float, help="USD per million input tokens")
    bench.add_argument("--output-price", type=float, help="USD per million output tokens")
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
    if args.command == "providers":
        print(json.dumps(registry(), indent=2))
    elif args.command == "dataset":
        if args.build:
            build(Path(args.path).parent)
        print(json.dumps(audit(load_cases(args.path)), indent=2))
    elif args.command == "compare-models":
        print(json.dumps(compare_models([read_json(p) for p in args.reports]), indent=2))
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
                                 args.engine, args.input_price, args.output_price, args.max_requests)
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
