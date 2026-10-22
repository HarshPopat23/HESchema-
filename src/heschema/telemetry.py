"""Prometheus telemetry and metrics instrumentation for HESchema service."""

from typing import Tuple

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

if HAS_PROMETHEUS:
    REQUESTS_TOTAL = Counter(
        "heschema_requests_total",
        "Total number of validation and completion requests",
        ["provider", "domain", "result"],
    )
    VALIDATION_LATENCY = Histogram(
        "heschema_validation_latency_seconds",
        "Validation and schema enforcement latency in seconds",
        buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    )
    REPAIR_ATTEMPTS = Counter(
        "heschema_repair_attempts_total",
        "Total number of schema repair attempts initiated",
    )
    ACTIVE_BENCHMARK_JOBS = Gauge(
        "heschema_active_benchmark_jobs",
        "Number of currently running benchmark jobs",
    )
else:
    REQUESTS_TOTAL = None
    VALIDATION_LATENCY = None
    REPAIR_ATTEMPTS = None
    ACTIVE_BENCHMARK_JOBS = None


def record_request(provider: str = "unknown", domain: str = "unknown", result: str = "unknown") -> None:
    if HAS_PROMETHEUS and REQUESTS_TOTAL:
        REQUESTS_TOTAL.labels(provider=provider, domain=domain, result=result).inc()


def record_validation_latency(duration_seconds: float) -> None:
    if HAS_PROMETHEUS and VALIDATION_LATENCY:
        VALIDATION_LATENCY.observe(duration_seconds)


def record_repair_attempt() -> None:
    if HAS_PROMETHEUS and REPAIR_ATTEMPTS:
        REPAIR_ATTEMPTS.inc()


def set_active_jobs(count: int) -> None:
    if HAS_PROMETHEUS and ACTIVE_BENCHMARK_JOBS:
        ACTIVE_BENCHMARK_JOBS.set(count)


def generate_metrics() -> Tuple[bytes, str]:
    if HAS_PROMETHEUS:
        return generate_latest(), CONTENT_TYPE_LATEST
    # Simple fallback format if prometheus_client is absent
    body = (
        "# HELP heschema_requests_total Total number of validation and completion requests\n"
        "# TYPE heschema_requests_total counter\n"
        'heschema_requests_total{provider="unknown",domain="unknown",result="unknown"} 0\n'
        "# HELP heschema_active_benchmark_jobs Number of currently running benchmark jobs\n"
        "# TYPE heschema_active_benchmark_jobs gauge\n"
        "heschema_active_benchmark_jobs 0\n"
    ).encode("utf-8")
    return body, CONTENT_TYPE_LATEST
