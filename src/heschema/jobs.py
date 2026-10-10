"""Background experiment job manager for browser-driven benchmarks."""

import asyncio
import datetime
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .benchmark import run
from .dataset import CATEGORIES, load_cases
from .domains import DOMAINS, reference_schema
from .jsonio import read_json
from .providers import ROOT, Provider
from .schema import check_schema

JOBS_ROOT = ROOT / "results/jobs"


class JobConflictError(Exception):
    """Raised when an operator already has an active background experiment."""


@dataclass
class JobRecord:
    id: str
    operator: str
    status: str  # queued, running, completed, failed, cancelled
    created_at: str
    completed_at: str | None = None
    error: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    progress: dict[str, Any] = field(default_factory=lambda: {
        "completedRuns": 0,
        "totalScheduled": 0,
        "requestsAttempted": 0,
        "providerErrors": 0,
        "currentCase": None,
        "currentArm": None,
        "currentRepeat": None
    })
    out_dir: Path = field(default_factory=Path)
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    task: asyncio.Task | None = None

    def public_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "createdAt": self.created_at,
            "completedAt": self.completed_at,
            "error": self.error,
            "params": {k: v for k, v in self.params.items() if k != "schema"},
            "hasCustomSchema": bool(self.params.get("schema")),
            "progress": self.progress
        }


class JobManager:
    def __init__(self, jobs_dir: Path = JOBS_ROOT):
        self.jobs_dir = Path(jobs_dir)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.jobs: dict[str, JobRecord] = {}
        self.lock = asyncio.Lock()

    def _check_single_active_job(self, operator: str):
        for job in self.jobs.values():
            if job.operator == operator and job.status in {"queued", "running"}:
                raise JobConflictError(f"Another benchmark job is already running (Job ID: {job.id}). Please wait or cancel it.")

    def select_cases(self, domain: str, preset: str, case_count: int | None = None):
        if domain not in DOMAINS:
            raise ValueError(f"Unknown domain: {domain}")
        all_cases = load_cases(ROOT / "benchmarks/cases.jsonl")
        domain_cases = [c for c in all_cases if c["domain"] == domain]
        if not domain_cases:
            raise ValueError(f"No benchmark cases found for domain: {domain}")

        if preset == "quick":
            # 2 cases per category across the 7 categories = 14 cases
            selected = []
            for cat in CATEGORIES:
                cat_cases = [c for c in domain_cases if c["category"] == cat]
                selected.extend(cat_cases[:2])
            return selected

        if preset == "full":
            return domain_cases

        # Custom preset
        count = max(1, min(len(domain_cases), case_count or 14))
        # Ensure category coverage if possible
        selected = []
        per_cat = max(1, count // len(CATEGORIES))
        for cat in CATEGORIES:
            cat_cases = [c for c in domain_cases if c["category"] == cat]
            selected.extend(cat_cases[:per_cat])
            if len(selected) >= count:
                break
        if len(selected) < count:
            remaining = [c for c in domain_cases if c not in selected]
            selected.extend(remaining[: count - len(selected)])
        return selected[:count]

    async def create_benchmark_job(
        self,
        domain: str,
        provider_name: str,
        model: str | None,
        schema: dict | bool | None,
        preset: str = "quick",
        case_count: int | None = None,
        repeats: int = 1,
        repairs: int = 0,
        interval: float | None = None,
        seed: int = 42,
        input_price: float | None = None,
        output_price: float | None = None,
        operator: str = "local-operator",
    ) -> JobRecord:
        async with self.lock:
            self._check_single_active_job(operator)

            if schema is not None:
                check_schema(schema)

            selected_cases = self.select_cases(domain, preset, case_count)
            now = datetime.datetime.now(datetime.timezone.utc)
            job_id = f"job_{now.strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}"
            out_dir = self.jobs_dir / job_id
            out_dir.mkdir(parents=True, exist_ok=True)

            total_scheduled = len(selected_cases) * repeats * 3

            record = JobRecord(
                id=job_id,
                operator=operator,
                status="queued",
                created_at=now.isoformat(),
                params={
                    "domain": domain,
                    "provider": provider_name,
                    "model": model,
                    "preset": preset,
                    "caseCount": len(selected_cases),
                    "repeats": repeats,
                    "repairs": repairs,
                    "interval": interval,
                    "seed": seed,
                    "inputPrice": input_price,
                    "outputPrice": output_price,
                    "schema": schema,
                },
                progress={
                    "completedRuns": 0,
                    "totalScheduled": total_scheduled,
                    "requestsAttempted": 0,
                    "providerErrors": 0,
                    "currentCase": None,
                    "currentArm": None,
                    "currentRepeat": None,
                },
                out_dir=out_dir,
                cancel_event=asyncio.Event(),
            )
            self.jobs[job_id] = record

            # Spawn background execution
            record.task = asyncio.create_task(self._run_job(record, selected_cases))
            return record

    async def _run_job(self, record: JobRecord, cases: list[dict]):
        record.status = "running"
        params = record.params
        provider = None
        try:
            provider = Provider(
                name=params["provider"],
                model=params.get("model"),
                interval=params.get("interval"),
            )

            def on_progress(p):
                record.progress.update(p)

            candidate_schema = params.get("schema")
            # If no custom schema provided, input_schema arm uses reference schema
            if candidate_schema is None:
                candidate_schema = reference_schema(params["domain"])

            await run(
                cases=cases,
                provider=provider,
                out=record.out_dir,
                candidate=candidate_schema,
                repeats=params["repeats"],
                repairs=params["repairs"],
                seed=params["seed"],
                backend="jsonschema",
                input_price=params.get("inputPrice"),
                output_price=params.get("outputPrice"),
                on_progress=on_progress,
                cancel_event=record.cancel_event,
            )

            if record.cancel_event.is_set():
                record.status = "cancelled"
            else:
                record.status = "completed"

        except Exception as exc:
            record.error = str(exc)
            if record.cancel_event.is_set():
                record.status = "cancelled"
            else:
                record.status = "failed"
        finally:
            if provider is not None:
                try:
                    await provider.close()
                except Exception:
                    pass
            record.completed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def get_job(self, job_id: str, operator: str) -> JobRecord:
        if job_id not in self.jobs:
            # Check if directory exists on disk from prior run
            disk_dir = self.jobs_dir / job_id
            if disk_dir.exists() and (disk_dir / "report.json").exists():
                return JobRecord(
                    id=job_id,
                    operator=operator,
                    status="completed",
                    created_at="persisted",
                    completed_at="persisted",
                    out_dir=disk_dir,
                )
            raise KeyError(f"Job {job_id} not found")
        job = self.jobs[job_id]
        if job.operator != operator and operator != "operator":
            raise KeyError(f"Job {job_id} not found")
        return job

    def cancel_job(self, job_id: str, operator: str) -> JobRecord:
        job = self.get_job(job_id, operator)
        if job.status in {"queued", "running"}:
            job.cancel_event.set()
            job.status = "cancelled"
        return job

    def get_report(self, job_id: str, operator: str) -> dict[str, Any]:
        job = self.get_job(job_id, operator)
        report_path = job.out_dir / "report.json"
        if not report_path.exists():
            raise FileNotFoundError(f"Report not yet available for job {job_id}")
        return read_json(report_path)

    def get_markdown_report(self, job_id: str, operator: str) -> str:
        job = self.get_job(job_id, operator)
        md_path = job.out_dir / "report.md"
        if not md_path.exists():
            raise FileNotFoundError(f"Markdown report not yet available for job {job_id}")
        return md_path.read_text(encoding="utf-8")

    def get_runs(self, job_id: str, operator: str, offset: int = 0, limit: int = 100) -> dict[str, Any]:
        job = self.get_job(job_id, operator)
        runs_path = job.out_dir / "runs.jsonl"
        if not runs_path.exists():
            return {"total": 0, "runs": [], "offset": offset, "limit": limit}
        from .jsonio import loads
        lines = [line.strip() for line in runs_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        total = len(lines)
        sliced = lines[offset: offset + limit]
        return {
            "total": total,
            "runs": [loads(line) for line in sliced],
            "offset": offset,
            "limit": limit
        }
