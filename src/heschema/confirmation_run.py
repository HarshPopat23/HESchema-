"""Checkpointed confirmation runner. Default command is an offline preflight.

One worker per explicitly supplied credential, never fail over on quota errors.
No output caching: repeats are independent provider calls. Raw traces stay in results/.
"""

import argparse
import asyncio
import json
import os
import random
import statistics
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .confirmation import PACK, audit, messages, oracle, sha, verify_freeze
from .contracts import Contract
from .jsonio import canonical
from .providers import Generation, Provider
from .repair import RepairLimits, coordinate, request_generation
from .schema import SchemaEngine
from .study_evidence import VERSION as EVIDENCE_VERSION
from .study_evidence import StudyEvidence, atomic_json
from .validation import validate_contract


def schedule(cases, protocol):
    rng = random.Random(protocol['seed'])
    groups = [(case['id'], model, repeat) for case in cases
              for model in protocol['models'] for repeat in range(protocol['repeats'])]
    rng.shuffle(groups)
    slots = []
    for case_id, model, repeat in groups:
        arms = list(protocol['arms'])
        rng.shuffle(arms)
        slots.extend({'caseId': case_id, 'model': model, 'repeat': repeat, 'arm': arm} for arm in arms)
    return slots


def slot_key(slot):
    return (slot['caseId'], slot['model'], slot['repeat'], slot['arm'])


def journal(path, item):
    with path.open('a') as stream:
        stream.write(canonical(item) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def read_journal(path):
    if not path.exists():
        return []
    # Fail closed on truncated/corrupt checkpoints; never silently drop usage evidence.
    return [json.loads(line) for line in path.read_text().splitlines()]


async def run_slot(provider, case, slot, protocol, previous=None, evidence=None):
    contract = Contract(**case['contract'])
    engine = SchemaEngine()

    def evaluate(generated):
        return validate_contract(generated.text, engine, contract, case['snapshot'], generation=generated)

    async def generate(prompt, attempt):
        return await request_generation(provider, prompt, protocol['seed'] + slot['repeat'],
                                        protocol['maxTokens'], protocol['temperature'])

    replay = None
    if previous and previous['result']['attempts']:
        replay = Generation(**previous['result']['attempts'][0]['generation'])
    result = await coordinate(generate, evaluate, messages(case, slot['arm']),
                              limits=RepairLimits(repairs=protocol['repairs'], max_requests=2,
                                                  max_tokens=protocol['maxTokens'], feedback_chars=1000,
                                                  deadline_seconds=180),
                              first_generation=replay, evidence=evidence)
    # Oracle is called only after repair and cannot affect prompts or retries.
    attempts = result['attempts']
    first_correct = oracle(case, attempts[0]['generation']['text']) if attempts else None
    final_correct = oracle(case, attempts[-1]['generation']['text']) if attempts else None
    observations = []
    for attempt in attempts:
        evaluation = attempt['evaluation']
        correct = oracle(case, attempt['generation']['text'])
        observations.append({'correct': correct, 'accepted': evaluation['accepted'],
                             'schemaAccepted': evaluation['referenceSchemaValid'] is True,
                             'requestMade': attempt['requestMade']})
    return {**slot, 'cluster': case['cluster'], 'family': case['family'],
            'firstCorrect': first_correct, 'finalCorrect': final_correct,
            'complete': result['failure'] is None and result['stopReason'] not in {'deadline', 'cancelled'},
            'observations': observations, 'result': result}


def summarize(rows, slots):
    latest = {slot_key(row): row for row in rows}
    complete = {key: row for key, row in latest.items() if row['complete']}
    matched = []
    groups = defaultdict(dict)
    for row in complete.values():
        groups[(row['caseId'], row['model'], row['repeat'])][row['arm']] = row
    for arms in groups.values():
        if set(arms) == {'full', 'compact'}:
            matched.extend(arms.values())
    arms = {}
    for arm in ('full', 'compact'):
        group = [r for r in matched if r['arm'] == arm]
        measured = [a['generation'] for r in group for a in r['result']['attempts'] if a['requestMade']]
        # Include usage from earlier checkpoints for these slots exactly once.
        historic = [r for r in rows if slot_key(r) in {slot_key(g) for g in group}]
        billed = [a['generation'] for r in historic for a in r['result']['attempts'] if a['requestMade']]
        token_known = all(g['input_tokens'] is not None and g['output_tokens'] is not None for g in billed)
        observations = [o for r in group for o in r['observations']]
        arms[arm] = {'matchedSlots': len(group), 'firstCorrect': sum(r['firstCorrect'] is True for r in group),
                     'finalCorrect': sum(r['finalCorrect'] is True for r in group),
                     'wrongAcceptedResponses': sum(o['accepted'] and not o['correct'] for o in observations),
                     'correctRejectedResponses': sum(not o['accepted'] and o['correct'] for o in observations),
                     'schemaOnlyWrongAcceptedResponses': sum(o['schemaAccepted'] and not o['correct'] for o in observations),
                     'returnedResponses': len(measured),
                     'totalTokensIncludingEarlierCheckpoints': sum(g['input_tokens'] + g['output_tokens'] for g in billed) if token_known else None,
                     'medianCoordinatorMs': statistics.median(r['result']['elapsedMs'] for r in group) if group else None,
                     'byModel': {}, 'byFamily': {}}
        for field, target in (('model', 'byModel'), ('family', 'byFamily')):
            for value in sorted({r[field] for r in group}):
                subset = [r for r in group if r[field] == value]
                arms[arm][target][value] = {'slots': len(subset),
                                           'firstCorrect': sum(r['firstCorrect'] is True for r in subset),
                                           'finalCorrect': sum(r['finalCorrect'] is True for r in subset)}
    all_generated = [a['generation'] for r in rows for a in r['result']['attempts'] if a['requestMade']]
    return {'plannedSlots': len(slots), 'completedSlots': len(complete), 'matchedPairs': len(matched) // 2,
            'tasks': len({r['caseId'] for r in complete.values()}),
            'sourceClusters': len({r['cluster'] for r in complete.values()}), 'arms': arms,
            'providerRequestsAttempted': sum(r['result']['requestsAttempted'] for r in rows),
            'returnedResponses': len(all_generated), 'billingVerified': False,
            'notice': 'Repeats are not independent tasks. Six project clusters limit generalization. Both arms retain contract validation; this is not a schema-only generation comparison.'}


async def execute(out, *, pack=PACK, keys=None, interval=10, provider_factory=Provider):
    pack, out = Path(pack), Path(out)
    freeze = verify_freeze(pack)
    audit(pack)
    protocol = json.loads((pack / 'protocol.json').read_text())
    cases = json.loads((pack / 'cases.json').read_text())
    slots = schedule(cases, protocol)
    keys = keys if keys is not None else [k.strip() for k in os.getenv('GROQ_API_KEYS', os.getenv('GROQ_API_KEY', '')).split(',') if k.strip()]
    if not keys or len(set(keys)) != len(keys):
        raise ValueError('Supply distinct authorized credentials in GROQ_API_KEYS or GROQ_API_KEY')
    if interval < protocol['minimumWorkerIntervalSeconds']:
        raise ValueError('Worker pacing cannot be shorter than the frozen protocol')
    out.mkdir(parents=True, exist_ok=True)
    code_paths = ('src/heschema/confirmation.py', 'src/heschema/confirmation_run.py', 'src/heschema/contract_prompt.py',
                  'src/heschema/providers.py', 'src/heschema/repair.py', 'src/heschema/validation.py',
                  'src/heschema/rules.py', 'src/heschema/context_schema.py', 'src/heschema/repair_feedback.py',
                  'src/heschema/study_evidence.py')
    root = Path(__file__).resolve().parents[2]
    config = {'freezeSha256': sha(pack / 'freeze.json'), 'protocol': protocol,
              'evidenceVersion': EVIDENCE_VERSION,
              'codeHashes': {p: sha(root / p) for p in code_paths}, 'workers': len(keys), 'interval': interval}
    target = out / 'config.json'
    if target.exists() and json.loads(target.read_text()) != config:
        raise ValueError('Resume configuration differs')
    target.write_text(json.dumps(config, indent=2) + '\n')
    (out / 'schedule.json').write_text(json.dumps(slots, indent=2) + '\n')
    evidence = StudyEvidence(out)
    rows = evidence.load_rows()
    evidence.set_schedule(slots)
    latest = {slot_key(row): row for row in rows}
    pending = [slot for slot in slots if not latest.get(slot_key(slot), {}).get('complete')]
    queue = asyncio.Queue()
    for slot in pending:
        queue.put_nowait(slot)
    by_id = {case['id']: case for case in cases}
    stopped = asyncio.Event()
    request_count = sum(row['result']['requestsAttempted'] for row in rows)
    request_limit = len(slots) * 2 + protocol['maximumQuotaRetries'] * len(keys)
    run_started = time.perf_counter()

    async def worker(index, key):
        nonlocal request_count
        providers = {}
        for model in protocol['models']:
            # Construct with an environment credential, then replace in memory only.
            old = os.environ.get('GROQ_API_KEY')
            os.environ['GROQ_API_KEY'] = key
            try:
                providers[model] = provider_factory('groq', model=model, interval=0)
            finally:
                if old is None:
                    os.environ.pop('GROQ_API_KEY', None)
                else:
                    os.environ['GROQ_API_KEY'] = old
        last_start = 0.0
        quota_retries = 0
        try:
            while not stopped.is_set():
                try:
                    slot = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                while not stopped.is_set():
                    if request_count + 2 > request_limit:
                        stopped.set()
                        break
                    wait = max(0, interval - (time.monotonic() - last_start))
                    # Pacing is outside coordinator latency, explicitly recorded here.
                    await asyncio.sleep(wait)
                    last_start = time.monotonic()
                    session = evidence.session(slot)
                    row = await run_slot(providers[slot['model']], by_id[slot['caseId']], slot, protocol,
                                         previous=latest.get(slot_key(slot)), evidence=session)
                    row.update(worker=index, dispatchWaitMs=wait * 1000,
                               recordedAt=datetime.now(timezone.utc).isoformat(),
                               freezeSha256=config['freezeSha256'])
                    request_count += row['result']['requestsAttempted']
                    row = session.commit(row, row['result'])
                    journal(out / 'runs.jsonl', row)
                    rows.append(row)
                    latest[slot_key(slot)] = row
                    atomic_json(out / 'summary.json', summarize(rows, slots) | {'evidence': evidence.audit()})
                    done = sum(r['complete'] for r in latest.values())
                    print(f'completed={done}/{len(slots)} requests={request_count}', flush=True)
                    failure = row['result']['failure']
                    if failure:
                        if failure.get('httpStatus') == 429 and quota_retries < protocol['maximumQuotaRetries']:
                            quota_retries += 1
                            journal(out / 'events.jsonl', {'worker': index, 'event': 'quota_wait',
                                                          'seconds': protocol['quotaWaitSeconds'],
                                                          'slot': slot, 'retry': quota_retries})
                            await asyncio.sleep(protocol['quotaWaitSeconds'])
                            continue
                        stopped.set()
                        print('Stopped after provider failure; preserved partial results.', flush=True)
                    break
        finally:
            for provider in providers.values():
                await provider.close()

    try:
        await asyncio.gather(*(worker(i, key) for i, key in enumerate(keys)))
    finally:
        evidence.audit()
    summary = summarize(rows, slots)
    summary.update(runWallMs=(time.perf_counter() - run_started) * 1000,
                   freezeCreatedAt=freeze['frozenAt'], stoppedAfterFailure=stopped.is_set())
    summary['evidence'] = evidence.audit()
    atomic_json(out / 'summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--out', type=Path, default=Path('results/confirmation-v1'))
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({'audit': audit(), 'freeze': verify_freeze(), 'status': 'offline_preflight'}, indent=2))
        return
    print(json.dumps(asyncio.run(execute(args.out)), indent=2))


if __name__ == '__main__':
    main()
