"""Nine-worker H60 latency replication. Never records credentials or private reasoning."""
import argparse
import asyncio
import hashlib
import json
import math
import os
import random
import statistics
import time
import uuid
from pathlib import Path

import httpx
import run_60_tasks_experiment as base
from jsonschema import Draft202012Validator, FormatChecker
from rescore_confirmation60 import correct

from heschema.calculations import validate_with_calculations
from heschema.jsonio import loads
from heschema.schema import SchemaEngine
from heschema.study_evidence import atomic_json
from heschema.validation import validate_contract

PARTS = ('pacingWaitMs', 'retryWaitMs', 'providerRoundTripMs',
         'localValidationMs', 'applicationCalculationMs', 'otherMs')


def persist(path, value):
    atomic_json(path, value)
    if json.loads(path.read_text()) != value:
        raise RuntimeError('Durable evidence readback mismatch')


def partition(total, values):
    values = dict(values)
    residual = total - sum(values.get(k, 0) for k in PARTS if k != 'otherMs')
    if residual < -0.001:
        raise ValueError('Overlapping timing components')
    values['otherMs'] = max(0, residual)
    return values


def verify_timing(timing):
    assert all(math.isfinite(timing[k]) and timing[k] >= 0 for k in (*PARTS, 'queueWaitMs', 'serviceTotalMs', 'endToEndMs'))
    assert abs(sum(timing[k] for k in PARTS) - timing['serviceTotalMs']) < 0.01
    assert abs(timing['queueWaitMs'] + timing['serviceTotalMs'] - timing['endToEndMs']) < 0.01


def detector(text, arm, case, contract, engine):
    if arm == 'A':
        try:
            doc = loads(text)
            errors = list(Draft202012Validator(contract.schema, format_checker=FormatChecker()).iter_errors(doc))
            return not errors, '\n'.join(e.message for e in errors), 0.0
        except (ValueError, TypeError):
            return False, 'Return only valid whole JSON', 0.0
    if arm == 'D' and case.get('d_calc'):
        result = validate_with_calculations(text, engine, contract, case['snapshot'])
    else:
        result = validate_contract(text, engine, contract, case['snapshot'])
    return result['accepted'], '\n'.join(e.get('message', '') for e in result['errors']), result.get('calculation', {}).get('computeMs', 0.0)


async def execute(out, keys, pilot=False, interval=15):
    if (out / 'manifest.json').exists():
        raise RuntimeError('Existing run: inspect evidence rather than blindly restarting calls')
    cases = json.loads((base.DATA_DIR / 'cases.json').read_text())
    if pilot:
        # Two tasks per family; engineering reuse is excluded from main inference.
        picked = []
        for family in sorted({c['family'] for c in cases}):
            picked += [c for c in cases if c['family'] == family][:2]
        cases = picked
    by_id = {c['id']: c for c in cases}
    if pilot:
        slots = [{'caseId': c['id'], 'model': base.MODELS[i % 3], 'repeat': 0, 'arm': a}
                 for i, c in enumerate(cases) for a in 'ABCD']
        random.Random(20261024).shuffle(slots)
    else:
        slots = base.build_schedule(cases, seed=20261024)
    persist(out / 'manifest.json', {
        'slots': slots, 'workers': len(keys), 'pilot': pilot, 'intervalSeconds': interval,
        'caseSha256': hashlib.sha256((base.DATA_DIR / 'cases.json').read_bytes()).hexdigest(),
        'codeHashes': {str(p.relative_to(base.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for folder in ('src/heschema', 'scripts') for p in sorted((base.ROOT / folder).rglob('*.py'))},
        'settings': {'mode': 'prompt_only', 'max_tokens': 2048, 'temperature': 0, 'repairs': 1},
        'scope': 'Fixed nine-worker batch replication; not serial latency or provider-internal inference time',
    })
    queue = asyncio.Queue()
    for i, slot in enumerate(slots):
        queue.put_nowait((i, slot))
    enqueued = time.perf_counter()
    async def worker(index, key):
        engine = SchemaEngine()
        last_start = 0.0
        async with httpx.AsyncClient(timeout=90) as client:
            try:
                while not queue.empty():
                    number, slot = queue.get_nowait()
                    started = time.perf_counter()
                    times = dict.fromkeys(PARTS[:-1], 0.0)
                    case = by_id[slot['caseId']]
                    messages, contract = base.build_messages_for_arm(case, slot['arm'])
                    returned = []
                    diagnostic = ''
                    for phase in ('initial', 'repair'):
                        if phase == 'repair':
                            messages = base.build_repair_message(messages, returned[0]['rawContent'], diagnostic)
                        for attempt in range(12):
                            wait = max(0, interval - (time.perf_counter() - last_start))
                            before = time.perf_counter()
                            if wait:
                                await asyncio.sleep(wait)
                            times['pacingWaitMs'] += (time.perf_counter() - before) * 1000
                            identity = uuid.uuid4().hex
                            receipt = {'id': identity, 'slotIndex': number, 'slot': slot, 'worker': index,
                                       'phase': phase, 'state': 'started', 'messages': messages}
                            path = out / 'requests' / (identity + '.json')
                            persist(path, receipt)
                            last_start = time.perf_counter()
                            try:
                                response = await client.post('https://api.groq.com/openai/v1/chat/completions',
                                    headers={'Authorization': 'Bearer ' + key},
                                    json={'model': slot['model'], 'messages': messages,
                                          'max_tokens': 2048, 'temperature': 0})
                                elapsed = (time.perf_counter() - last_start) * 1000
                                times['providerRoundTripMs'] += elapsed
                                receipt.update(status=response.status_code, roundTripMs=elapsed)
                                if response.status_code == 200:
                                    data = response.json()
                                    choice = data['choices'][0]
                                    receipt.update(state='returned', rawContent=choice['message'].get('content') or '',
                                        usage=data.get('usage', {}), responseId=data.get('id'),
                                        resolvedModel=data.get('model'), finishReason=choice.get('finish_reason'))
                                    persist(path, receipt)
                                    returned.append(receipt)
                                    break
                                receipt['state'] = 'failed'
                                persist(path, receipt)
                                if response.status_code not in {429, 500, 502, 503, 504}:
                                    raise RuntimeError(f'HTTP {response.status_code}; worker {index}')
                                try:
                                    retry = max(60, float(response.headers.get('retry-after', 60)))
                                except ValueError:
                                    retry = 60
                            except (httpx.TransportError, httpx.TimeoutException) as exc:
                                elapsed = (time.perf_counter() - last_start) * 1000
                                times['providerRoundTripMs'] += elapsed
                                receipt.update(state='failed', errorType=type(exc).__name__, roundTripMs=elapsed)
                                persist(path, receipt)
                                retry = 60
                            before = time.perf_counter()
                            await asyncio.sleep(retry)
                            times['retryWaitMs'] += (time.perf_counter() - before) * 1000
                        else:
                            raise RuntimeError('Retry budget exhausted; preserve incomplete schedule')
                        before = time.perf_counter()
                        accepted, diagnostic, calculation = detector(returned[-1]['rawContent'], slot['arm'], case, contract, engine)
                        evaluation = (time.perf_counter() - before) * 1000
                        times['applicationCalculationMs'] += calculation
                        times['localValidationMs'] += evaluation - calculation
                        if accepted or not returned[-1]['rawContent']:
                            break
                    service = (time.perf_counter() - started) * 1000
                    timing = {**partition(service, times), 'queueWaitMs': (started-enqueued)*1000,
                              'serviceTotalMs': service, 'endToEndMs': (started-enqueued)*1000+service}
                    verify_timing(timing)
                    # Oracle scoring is offline and outside the measured service interval.
                    persist(out / 'slots' / f'{number:04}.json', {
                        **slot, 'slotIndex': number, 'requestIds': [r['id'] for r in returned],
                        'accepted': accepted, 'timing': timing,
                        'timingBoundary': 'worker start to final validation decision; excludes final audit-file persistence',
                    })
                    queue.task_done()
            finally:
                engine.close()
    await asyncio.gather(*(worker(i, key) for i, key in enumerate(keys)))


def verify(out):
    manifest = json.loads((out / 'manifest.json').read_text())
    for path, digest in manifest['codeHashes'].items():
        assert hashlib.sha256((base.ROOT / path).read_bytes()).hexdigest() == digest, path
    cases = {c['id']: c for c in json.loads((base.DATA_DIR / 'cases.json').read_text())}
    slots = [json.loads(p.read_text()) for p in sorted((out / 'slots').glob('*.json'))]
    assert len(slots) == len(manifest['slots'])
    assert {s['slotIndex'] for s in slots} == set(range(len(manifest['slots'])))
    receipts = {p.stem: json.loads(p.read_text()) for p in (out / 'requests').glob('*.json')}
    assert all(r['state'] in {'returned', 'failed'} for r in receipts.values())
    for s in slots:
        verify_timing(s['timing'])
        assert all(s[k] == manifest['slots'][s['slotIndex']][k] for k in ('caseId', 'model', 'repeat', 'arm'))
        chosen = [receipts[i] for i in s['requestIds']]
        assert 1 <= len(chosen) <= 2
        assert all(r['state'] == 'returned' and r['slotIndex'] == s['slotIndex'] for r in chosen)
        physical = [r for r in receipts.values() if r['slotIndex'] == s['slotIndex']]
        assert abs(sum(r['roundTripMs'] for r in physical) - s['timing']['providerRoundTripMs']) < 0.01
        s['firstCorrect'] = correct(chosen[0]['rawContent'], cases[s['caseId']], s['arm'])
        s['finalCorrect'] = correct(chosen[-1]['rawContent'], cases[s['caseId']], s['arm'])
        s['totalTokens'] = sum(r['usage']['prompt_tokens']+r['usage']['completion_tokens'] for r in chosen)
    def metrics(rows):
        result = {'n': len(rows), 'firstCorrect': sum(r['firstCorrect'] for r in rows),
                  'finalCorrect': sum(r['finalCorrect'] for r in rows),
                  'wrongAccepted': sum(r['accepted'] and not r['finalCorrect'] for r in rows),
                  'totalTokens': sum(r['totalTokens'] for r in rows)}
        for field in (*PARTS, 'queueWaitMs', 'serviceTotalMs', 'endToEndMs'):
            values = sorted(r['timing'][field] for r in rows)
            result[field] = {'median': statistics.median(values), 'p95': values[math.ceil(.95*len(values))-1]}
        return result
    summary = {'byArm': {a: metrics([s for s in slots if s['arm']==a]) for a in 'ABCD'},
               'byModelArm': {m:{a:metrics([s for s in slots if s['arm']==a and s['model']==m]) for a in 'ABCD'} for m in base.MODELS},
               'requests': len(receipts), 'workers': manifest['workers'], 'pilot': manifest['pilot']}
    atomic_json(out / 'summary.json', summary)
    report = ['# H60 latency study', '',
        'Nine fixed workers across supplied credentials. Organization independence is not verified. This is a parallel batch replication, not single-user serial latency.', '',
        '| Arm | N | Final correct | Service median ms | Service p95 ms | HTTP median ms | Retry wait median ms |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for a,m in summary['byArm'].items():
        report.append(f"| {a} | {m['n']} | {m['finalCorrect']} | {m['serviceTotalMs']['median']:.1f} | {m['serviceTotalMs']['p95']:.1f} | {m['providerRoundTripMs']['median']:.1f} | {m['retryWaitMs']['median']:.1f} |")
    report += ['', '## Scope', '',
        '- Queue wait is time in the batch scheduler, not an intrinsic model cost. End-to-end includes that queue; service time excludes it.',
        '- Service time includes preparation, pacing, HTTP round trips, retry waits, local validation and calculations; other time includes receipt persistence and processing.',
        '- Final slot audit-file persistence is outside the response-ready service boundary. No timer includes the offline correctness oracle.',
        '- HTTP round trip includes network and remote queueing; it is not pure model inference or streaming time to first token.',
        '- p95 uses the nearest-rank definition. Timing components are disjoint; their percentile values need not add to the total percentile.',
        '- Rate limits, provider load, existing task exposure and nine-worker interference limit causal claims. This study alone cannot establish a universal speed improvement.',
        '- Counts/sums in D measure assembled system output. The task pack is reused public-record adaptations, not organic production prompts.',
        '- Local slot/receipt verification is required before reporting. Incomplete schedules are not successful studies.']
    (out / 'REPORT.md').write_text('\n'.join(report)+'\n')
    print('LATENCY_EVIDENCE_VERIFIED')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['run', 'verify'])
    parser.add_argument('out', type=Path)
    parser.add_argument('--pilot', action='store_true')
    args = parser.parse_args()
    if args.action == 'verify':
        verify(args.out)
    else:
        keys = [k for k in Path(os.environ['H60_CREDENTIAL_FILE']).read_text().splitlines() if k]
        assert len(keys) == 9 and len(set(keys)) == 9
        asyncio.run(execute(args.out, keys, args.pilot))
