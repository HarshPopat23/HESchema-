"""Client-observed wall-clock phases; no inference-time or historical imputations."""

import time
from contextlib import asynccontextmanager, contextmanager
from math import isfinite

VERSION = 'latency-v1'
PROVIDER_PHASES = ('providerResponseMs', 'queueWaitMs', 'pacingWaitMs', 'retryWaitMs', 'adapterOtherMs')
RUN_PHASES = ('totalMs', 'requestWallMs', 'localEvaluationMs', 'localValidationMs', 'applicationCalculationMs', 'coordinatorOtherMs')


def duration(value):
    return type(value) in {int, float} and isfinite(value) and value >= 0


def milliseconds(start):
    return max(0.0, (time.perf_counter() - start) * 1000)


class ProviderTiming:
    def __init__(self):
        self.started = time.perf_counter()
        self.values = dict.fromkeys(PROVIDER_PHASES[:-1], 0.0)
        self.http_attempts = []

    @contextmanager
    def phase(self, key):
        started = time.perf_counter()
        try:
            yield
        finally:
            self.values[key] += milliseconds(started)

    @asynccontextmanager
    async def lock(self, lock):
        with self.phase('queueWaitMs'):
            await lock.acquire()
        try:
            yield
        finally:
            lock.release()

    @contextmanager
    def http_attempt(self):
        started = time.perf_counter()
        record = {'httpStatus': None, 'outcome': 'returned'}
        self.http_attempts.append(record)
        try:
            yield record
        except BaseException as exc:
            record['outcome'] = type(exc).__name__
            raise
        finally:
            record['responseMs'] = milliseconds(started)
            self.values['providerResponseMs'] += record['responseMs']

    def snapshot(self):
        total = milliseconds(self.started)
        return {'version': VERSION, 'scope': 'provider_adapter', 'totalMs': total,
                **self.values, 'adapterOtherMs': max(0.0, total - sum(self.values.values())),
                'httpAttempts': self.http_attempts.copy()}


def coordinator_timing(ledger, *, total_ms, evaluation_ms, calculation_ms):
    """Request wall time contains the provider subphases; do not add both."""
    actual = [entry for entry in ledger if entry.get('requestInvoked')]
    request_wall = sum(entry.get('requestWallMs', 0) for entry in ledger)
    provider = [entry['providerTiming'] for entry in actual
                if (entry.get('providerTiming') or {}).get('version') == VERSION
                and entry['providerTiming'].get('scope') == 'provider_adapter'
                and all(duration(entry['providerTiming'].get(key)) for key in PROVIDER_PHASES)]
    complete = len(provider) == len(actual)
    return {'version': VERSION, 'scope': 'repair_coordinator', 'totalMs': total_ms,
            'requestWallMs': request_wall, 'localEvaluationMs': evaluation_ms,
            'localValidationMs': max(0.0, evaluation_ms - calculation_ms) if calculation_ms is not None else None,
            'applicationCalculationMs': calculation_ms,
            'coordinatorOtherMs': max(0.0, total_ms - request_wall - evaluation_ms),
            'providerBreakdownComplete': complete, 'providerCallsMeasured': len(provider),
            'providerCallsUnmeasured': len(actual) - len(provider),
            **{key: sum(p[key] for p in provider) if complete else None for key in PROVIDER_PHASES},
            'replayedResponses': sum(entry.get('status') == 'replayed' for entry in ledger)}


def summarize_timing(rows):
    """Summarize known observations with denominators, including failed outcomes."""
    def summarize(group):
        summary = {}
        for key in (*RUN_PHASES, *PROVIDER_PHASES):
            values = [r['timing'][key] for r in group
                      if (r.get('timing') or {}).get('version') == VERSION
                      and r['timing'].get('scope') == 'repair_coordinator'
                      and duration(r['timing'].get(key))]
            values.sort()
            def percentile(fraction):
                if not values:
                    return None
                index = (len(values) - 1) * fraction
                lower = int(index)
                upper = min(lower + 1, len(values) - 1)
                return values[lower] + (values[upper] - values[lower]) * (index - lower)
            summary[key] = {'measured': len(values), 'missing': len(group) - len(values),
                            'totalMs': sum(values) if values else None,
                            'meanMs': sum(values) / len(values) if values else None,
                            'p50Ms': percentile(.5), 'p95Ms': percentile(.95)}
        return summary
    return {'version': VERSION, 'scope': 'repair_coordinator', 'allOutcomes': summarize(rows),
            'byOutcome': {status: summarize([r for r in rows if r['status'] == status])
                          for status in sorted({r['status'] for r in rows})},
            'notice': 'Provider subphases are inside requestWallMs; validation/calculation are inside localEvaluationMs. Unknown/legacy phases stay missing. Replayed initial provider latency is excluded. Client-observed response time is not inference time.'}
