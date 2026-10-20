"""Deterministic timing controls; these are not live-provider speed benchmarks."""

import asyncio
import copy

import httpx
import pytest

from heschema.calculations import validate_with_calculations
from heschema.context_schema import ContextError
from heschema.contracts import Contract
from heschema.jsonio import read_json
from heschema.providers import ROOT, Generation, Provider, ProviderError
from heschema.repair import RepairLimits, coordinate, request_generation
from heschema.schema import SchemaEngine
from heschema.timing import ProviderTiming, coordinator_timing, summarize_timing

MESSAGES = [{'role': 'user', 'content': 'Return JSON.'}]


class Clock:
    now = 1000.0

    def read(self):
        return self.now

    def advance(self, ms):
        self.now += ms / 1000

    async def sleep(self, seconds):
        self.now += seconds


@pytest.fixture
def clock(monkeypatch):
    clock = Clock()
    monkeypatch.setattr('heschema.timing.time.perf_counter', clock.read)
    monkeypatch.setenv('GROQ_API_KEY', 'test-only-key')
    return clock


def body():
    return {'choices': [{'message': {'content': '{}'}, 'finish_reason': 'stop'}]}


def assert_partition(timing):
    assert timing['totalMs'] == pytest.approx(
        timing['requestWallMs'] + timing['localEvaluationMs'] + timing['coordinatorOtherMs'])
    if timing['applicationCalculationMs'] is not None:
        assert timing['localEvaluationMs'] == pytest.approx(
            timing['localValidationMs'] + timing['applicationCalculationMs'])


def test_response_time_excludes_pacing_and_retry_waits(clock, monkeypatch):
    monkeypatch.setattr('heschema.providers.time.monotonic', clock.read)
    monkeypatch.setattr('heschema.providers.asyncio.sleep', clock.sleep)
    calls = []
    def handler(request):
        calls.append(request)
        clock.advance(120 if len(calls) == 1 else 80)
        return (httpx.Response(429, headers={'retry-after': '2'}) if len(calls) == 1
                else httpx.Response(200, json=body()))
    async def run():
        provider = Provider('groq', interval=1, transport=httpx.MockTransport(handler))
        provider.last_request = clock.now
        try:
            generated = await provider.generate(MESSAGES)
        finally:
            await provider.close()
        timing = generated.metadata['timing']
        assert timing['providerResponseMs'] == pytest.approx(200)
        assert timing['pacingWaitMs'] == pytest.approx(1000)
        assert timing['retryWaitMs'] == pytest.approx(2000)
        assert timing['totalMs'] == pytest.approx(3200)
        assert [r['httpStatus'] for r in timing['httpAttempts']] == [429, 200]
        assert generated.transport_retries == 1
        assert generated.diagnostic()['timing'] == timing
        # This legacy field intentionally still contains retry time.
        assert generated.latency_ms == pytest.approx(2200)
    asyncio.run(run())


def test_adapter_lock_wait_is_not_provider_response_time(clock):
    async def handler(request):
        clock.advance(50)
        return httpx.Response(200, json=body())
    async def run():
        provider = Provider('groq', interval=0, transport=httpx.MockTransport(handler))
        await provider.lock.acquire()
        task = asyncio.create_task(provider.generate(MESSAGES))
        await asyncio.sleep(0)
        clock.advance(250)
        provider.lock.release()
        try:
            timing = (await task).metadata['timing']
        finally:
            await provider.close()
        assert timing['queueWaitMs'] == pytest.approx(250)
        assert timing['providerResponseMs'] == pytest.approx(50)
        assert timing['totalMs'] == pytest.approx(300)
    asyncio.run(run())


@pytest.mark.parametrize('failure', ['http', 'timeout', 'network', 'bad_response', 'long_backoff'])
def test_provider_failures_retain_sanitized_phase_evidence(clock, failure):
    def handler(request):
        clock.advance(75)
        if failure == 'timeout':
            raise httpx.ReadTimeout('private-test-key', request=request)
        if failure == 'network':
            raise httpx.ConnectError('private-test-key', request=request)
        if failure == 'bad_response':
            return httpx.Response(200, text='private-test-key')
        if failure == 'long_backoff':
            return httpx.Response(429, headers={'retry-after': '120'}, text='private-test-key')
        return httpx.Response(401, text='private-test-key')
    async def run():
        provider = Provider('groq', interval=0, transport=httpx.MockTransport(handler))
        try:
            with pytest.raises(ProviderError) as caught:
                await provider.generate(MESSAGES, retry=failure == 'long_backoff')
        finally:
            await provider.close()
        error = caught.value.diagnostic()
        assert error['requests'] == 1
        assert error['timing']['providerResponseMs'] == pytest.approx(75)
        assert error['timing']['retryWaitMs'] == 0
        assert 'private-test-key' not in str(error)
    asyncio.run(run())


def test_coordinator_partitions_each_attempt_and_counts_semantic_repairs(clock, monkeypatch):
    monkeypatch.setattr('heschema.providers.time.monotonic', clock.read)
    monkeypatch.setattr('heschema.providers.asyncio.sleep', clock.sleep)
    calls = []
    def handler(request):
        calls.append(request)
        clock.advance(100)
        return httpx.Response(200, json=body())
    def evaluate(generated):
        clock.advance(20)
        return {'accepted': len(calls) == 2, 'parsed': {}, 'calculation': {'computeMs': 10},
                'errors': [{'code': 'RELATION_MISMATCH', 'kind': 'count_equals'}]}
    async def run():
        provider = Provider('groq', interval=.3, transport=httpx.MockTransport(handler))
        try:
            result = await coordinate(lambda messages, i: request_generation(provider, messages, 0, 1024, 0),
                                      evaluate, MESSAGES, limits=RepairLimits(1))
        finally:
            await provider.close()
        timing = result['timing']
        assert_partition(timing)
        assert timing['totalMs'] == pytest.approx(420)
        assert timing['requestWallMs'] == pytest.approx(380)
        assert timing['providerResponseMs'] == pytest.approx(200)
        assert timing['pacingWaitMs'] == pytest.approx(180)
        assert timing['retryWaitMs'] == 0  # Transport retries disabled; repair call still paced.
        assert timing['localValidationMs'] == pytest.approx(20)
        assert timing['applicationCalculationMs'] == pytest.approx(20)
        assert result['elapsedMs'] == timing['totalMs']
        assert result['requestsAttempted'] == 2 and result['repairAttempts'] == 1
        assert result['requestLedger'][0]['requestWallMs'] == pytest.approx(100)
        # The old ledger timer includes local evaluation; the new request timer does not.
        assert result['requestLedger'][0]['elapsedMs'] == pytest.approx(120)
    asyncio.run(run())


def test_replayed_response_does_not_charge_old_provider_time(clock):
    old_timing = ProviderTiming().snapshot()
    old_timing['providerResponseMs'] = 100000
    old_timing['totalMs'] = 100000
    replay = Generation('{}', latency_ms=100000, metadata={'timing': old_timing})
    async def generate(messages, attempt):
        timer = ProviderTiming()
        with timer.http_attempt():
            clock.advance(30)
        return Generation('{}', metadata={'timing': timer.snapshot()})
    evaluations = []
    def evaluate(generated):
        evaluations.append(generated)
        clock.advance(5)
        return {'accepted': len(evaluations) == 2, 'errors': [{'code': 'JSON_INVALID'}]}
    result = asyncio.run(coordinate(generate, evaluate, [], first_generation=replay, limits=RepairLimits(1)))
    assert result['timing']['providerResponseMs'] == pytest.approx(30)
    assert result['timing']['requestWallMs'] == pytest.approx(30)
    assert result['timing']['localValidationMs'] == pytest.approx(10)
    assert result['timing']['replayedResponses'] == 1
    assert result['requestsAttempted'] == 1
    assert_partition(result['timing'])


@pytest.mark.parametrize('partial', [None, {'version': 'latency-v1', 'scope': 'provider_adapter'}])
def test_opaque_or_partial_adapter_timings_are_unknown_not_zero(clock, partial):
    async def generate(messages, attempt):
        clock.advance(40)
        return Generation('{}', latency_ms=999999, metadata={'timing': partial})
    result = asyncio.run(coordinate(generate, lambda g: {'accepted': True}, []))
    timing = result['timing']
    assert timing['requestWallMs'] == pytest.approx(40)
    assert timing['providerResponseMs'] is None and timing['retryWaitMs'] is None
    assert not timing['providerBreakdownComplete'] and timing['providerCallsUnmeasured'] == 1
    assert_partition(timing)


def test_cancelled_inflight_call_keeps_wall_time_without_fabricating_phases(clock):
    async def run():
        cancel = asyncio.Event()
        async def generate(messages, attempt):
            clock.advance(60)
            cancel.set()
            await asyncio.Event().wait()
        result = await coordinate(generate, lambda g: {'accepted': False}, [], cancel_event=cancel)
        assert result['stopReason'] == 'cancelled'
        assert result['timing']['requestWallMs'] == pytest.approx(60)
        assert result['timing']['providerResponseMs'] is None
        assert not result['timing']['providerBreakdownComplete']
        assert_partition(result['timing'])
    asyncio.run(run())


def test_budget_stop_has_zero_calls_and_measures_fallback_evaluation(clock):
    async def generate(messages, attempt):
        raise AssertionError('No request is allowed')
    def evaluate(generated):
        clock.advance(7)
        return {'accepted': False}
    result = asyncio.run(coordinate(generate, evaluate, [], limits=RepairLimits(max_requests=0)))
    assert result['stopReason'] == 'request_budget'
    assert result['timing']['requestWallMs'] == 0
    assert result['timing']['providerCallsMeasured'] == 0
    assert result['timing']['localValidationMs'] == pytest.approx(7)
    assert_partition(result['timing'])


def test_async_context_error_during_evaluation_preserves_timing_and_stop(clock):
    async def generate(messages, attempt):
        clock.advance(30)
        return Generation('{}')
    async def evaluate(generated):
        clock.advance(5)
        raise ContextError('Approval expired')
    result = asyncio.run(coordinate(generate, evaluate, [], limits=RepairLimits(2)))
    assert result['stopReason'] == 'context_changed' and result['requestsAttempted'] == 1
    assert result['timing']['requestWallMs'] == pytest.approx(30)
    assert result['timing']['localEvaluationMs'] == pytest.approx(10)  # Includes failed fallback.
    assert not result['finalEvaluation']['accepted']
    assert_partition(result['timing'])


@pytest.mark.parametrize('value', [None, -1, float('nan'), float('inf'), 1000])
def test_uninstrumented_or_invalid_calculation_split_stays_unknown(clock, value):
    async def generate(messages, attempt):
        return Generation('{}')
    def evaluate(generated):
        clock.advance(5)
        return {'accepted': True, 'calculation': {'computeMs': value}}
    result = asyncio.run(coordinate(generate, evaluate, []))
    assert result['timing']['localEvaluationMs'] == pytest.approx(5)
    assert result['timing']['localValidationMs'] is None
    assert result['timing']['applicationCalculationMs'] is None
    assert_partition(result['timing'])


def test_calculations_report_only_explicit_arithmetic_time(clock, monkeypatch):
    from heschema.calculations import calculation_value
    monkeypatch.setattr('heschema.calculations.perf_counter', clock.read)
    def compute(document, rule):
        clock.advance(5)
        return calculation_value(document, rule)
    monkeypatch.setattr('heschema.calculations.calculation_value', compute)
    example = read_json(ROOT / 'examples/contracts/application-calculations.json')
    contract = Contract(**example['contract'])
    context = {'id': 'control', 'version': 1, 'confirmed': True, 'facts': [], **example['context']}
    engine = SchemaEngine()
    try:
        result = validate_with_calculations(example['modelOutput'], engine, contract, context)
        assert result['accepted'] and result['parsed'] == example['expectedOutput']
        assert result['calculation']['computeMs'] == pytest.approx(10)
        assert result['calculation']['pipelineMs'] == pytest.approx(10)
        blocked = validate_with_calculations({'items': []}, engine, contract, context)
        assert not blocked['accepted'] and blocked['calculation']['computeMs'] == 0
    finally:
        engine.close()


def test_failed_attempt_timing_reaches_coordinator_and_report(clock):
    def handler(request):
        clock.advance(90)
        return httpx.Response(503)
    async def run():
        provider = Provider('groq', interval=0, transport=httpx.MockTransport(handler))
        try:
            return await coordinate(lambda messages, i: request_generation(provider, messages, 0, 1024, 0),
                                    lambda g: {'accepted': False}, [])
        finally:
            await provider.close()
    result = asyncio.run(run())
    assert result['failure']['timing']['providerResponseMs'] == pytest.approx(90)
    assert result['timing']['providerResponseMs'] == pytest.approx(90)
    assert result['timing']['providerBreakdownComplete']
    report = summarize_timing([{'status': 'provider_error', 'timing': result['timing']}])
    assert report['byOutcome']['provider_error']['providerResponseMs']['measured'] == 1


def test_legacy_missing_and_partial_timings_stay_missing_in_reports():
    timing = coordinator_timing([], total_ms=30, evaluation_ms=10, calculation_ms=0)
    timing['providerResponseMs'] = 20
    failed = {**timing, 'totalMs': 70, 'providerResponseMs': None}
    rows = [{'status': 'ok', 'timing': timing}, {'status': 'provider_error', 'timing': failed},
            {'status': 'ok', 'latencyMs': 1000}]
    before = copy.deepcopy(rows)
    report = summarize_timing(rows)
    assert rows == before
    total = report['allOutcomes']['totalMs']
    assert total == {'measured': 2, 'missing': 1, 'totalMs': 100, 'meanMs': 50, 'p50Ms': 50, 'p95Ms': 68}
    response = report['allOutcomes']['providerResponseMs']
    assert response['measured'] == 1 and response['missing'] == 2 and response['meanMs'] == 20
    assert report['byOutcome']['provider_error']['providerResponseMs']['totalMs'] is None
    assert summarize_timing([])['allOutcomes']['totalMs']['p95Ms'] is None


@pytest.mark.parametrize('value', [None, -1, float('nan'), float('inf'), '12', True])
def test_invalid_duration_is_not_a_reported_measurement(value):
    timing = coordinator_timing([], total_ms=30, evaluation_ms=10, calculation_ms=0)
    timing['providerResponseMs'] = value
    result = summarize_timing([{'status': 'ok', 'timing': timing}])
    assert result['allOutcomes']['providerResponseMs']['measured'] == 0
