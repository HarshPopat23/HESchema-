"""Export only this new public-source run and recompute its evidence independently.

Never accepts historical private study archives. Reasoning, credentials and headers
are not exported. Exact final response content is retained for re-scoring.
"""

import argparse
import hashlib
import json
import random
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from heschema.confirmation import PACK, oracle, sha, verify_freeze
from heschema.confirmation_run import read_journal, schedule, slot_key, summarize
from heschema.contracts import Contract
from heschema.failure_categories import classify
from heschema.jsonio import canonical
from heschema.providers import Generation
from heschema.schema import SchemaEngine
from heschema.timing import summarize_timing
from heschema.validation import validate_contract


def fenced_payload_diagnostic(case, text):
    """Describe invalid Markdown-wrapped content without changing any pass/fail."""
    match = re.fullmatch(r'\s*```(?:json)?[ \t]*\n(.*?)\n```\s*', text, re.DOTALL)
    return oracle(case, match.group(1)) if match else None


def paired_analysis(rows, repeats=10000):
    """Average repeats/models within tasks before resampling whole source projects."""
    groups = defaultdict(dict)
    for row in rows:
        if row['complete']:
            groups[(row['caseId'], row['model'], row['repeat'])][row['arm']] = row
    matched = [group for group in groups.values() if set(group) == {'full', 'compact'}]
    results = {}
    for outcome in ('firstCorrect', 'finalCorrect'):
        tasks = defaultdict(list)
        task_clusters = {}
        wins = losses = ties = 0
        for group in matched:
            full, compact = group['full'], group['compact']
            difference = int(compact[outcome] is True) - int(full[outcome] is True)
            tasks[full['caseId']].append(difference)
            task_clusters[full['caseId']] = full['cluster']
            wins += difference > 0
            losses += difference < 0
            ties += difference == 0
        task_means = {k: statistics.mean(v) for k, v in tasks.items()}
        cluster_values = defaultdict(list)
        for task, value in task_means.items():
            cluster_values[task_clusters[task]].append(value)
        rng = random.Random(20261020)
        names = sorted(cluster_values)
        boot = sorted(statistics.mean(value for name in (rng.choice(names) for _ in names)
                                      for value in cluster_values[name]) * 100
                      for _ in range(repeats)) if names else []
        results[outcome] = {'matchedPairs': len(matched), 'compactWins': wins, 'fullWins': losses, 'ties': ties,
                            'meanTaskDifferencePp': statistics.mean(statistics.mean(v) for v in tasks.values()) * 100 if tasks else None,
                            'clusterBootstrap95Pp': [boot[int(.025 * repeats)], boot[int(.975 * repeats)]] if boot else None,
                            'sourceClusters': len(cluster_values),
                            'byTaskDifferencePp': {k: statistics.mean(v) * 100 for k, v in tasks.items()}}
    return {'outcomes': results,
            'notice': 'Resamples entire source projects, preserving within-project repeats and models. Six clusters and shared templates limit precision. A zero-width empirical bootstrap interval in a ceiling-effect sample does not prove zero population error.'}


def export(run_dir, target=PACK / 'evidence'):
    freeze = verify_freeze()
    protocol = json.loads((PACK / 'protocol.json').read_text())
    cases = json.loads((PACK / 'cases.json').read_text())
    by_id = {c['id']: c for c in cases}
    run_dir, target = Path(run_dir), Path(target)
    config = json.loads((run_dir / 'config.json').read_text())
    if config['freezeSha256'] != sha(PACK / 'freeze.json') or config['protocol'] != protocol:
        raise ValueError('This exporter only accepts confirmation-v1, never previous archives')
    root = Path(__file__).resolve().parents[1]
    if any(sha(root / path) != expected for path, expected in config.get('codeHashes', {}).items()):
        raise ValueError('Measured runtime changed; revalidate using its preserved implementation')
    rows = read_journal(run_dir / 'runs.jsonl')
    slots = schedule(cases, protocol)
    allowed_slots = {slot_key(s) for s in slots}
    responses, checkpoints, failures = [], [], []
    engine = SchemaEngine()
    for checkpoint_index, row in enumerate(rows):
        case = by_id[row['caseId']]
        if slot_key(row) not in allowed_slots or row['freezeSha256'] != config['freezeSha256']:
            raise ValueError('Unfrozen or unexpected slot')
        if datetime.fromisoformat(row['recordedAt']) < datetime.fromisoformat(freeze['frozenAt']):
            raise ValueError('Response checkpoint predates the frozen protocol')
        result = row['result']
        expected_first = oracle(case, result['attempts'][0]['generation']['text']) if result['attempts'] else None
        expected_final = oracle(case, result['attempts'][-1]['generation']['text']) if result['attempts'] else None
        if (row['firstCorrect'], row['finalCorrect']) != (expected_first, expected_final):
            raise ValueError('Saved slot outcome differs on re-score')
        for attempt_index, attempt in enumerate(result['attempts']):
            generated = attempt['generation']
            if generated['model'] != row['model'] or not generated['metadata'].get('resolvedModelConfirmed'):
                raise ValueError('Cannot publish unconfirmed or mock model results')
            correct = oracle(case, generated['text'])
            if correct != row['observations'][attempt_index]['correct']:
                raise ValueError('Saved oracle judgment differs on re-score')
            evaluation = attempt['evaluation']
            replayed = validate_contract(generated['text'], engine, Contract(**case['contract']),
                                         case['snapshot'], generation=Generation(**generated))
            if replayed['accepted'] != evaluation['accepted']:
                raise ValueError('Recorded contract acceptance differs on replay')
            if attempt['requestMade']:
                output = {key: row[key] for key in ('caseId', 'model', 'repeat', 'arm', 'family', 'cluster')}
                output.update(checkpoint=checkpoint_index, attempt=attempt_index,
                              text=generated['text'], textSha256=hashlib.sha256(generated['text'].encode()).hexdigest(),
                              finishReason=generated['metadata'].get('finish_reason'),
                              responseId=generated['metadata'].get('responseId'),
                              systemFingerprint=generated['metadata'].get('systemFingerprint'),
                              inputTokens=generated['input_tokens'], outputTokens=generated['output_tokens'],
                              requestControls=generated['metadata'].get('requestControls'),
                              correct=correct, accepted=evaluation['accepted'],
                              schemaAccepted=evaluation['referenceSchemaValid'],
                              stages=evaluation['stages'], ruleChecks=evaluation['relationships']['rules'],
                              failureCategories=classify(evaluation, generation=generated),
                              fencedPayloadSemanticCorrect=fenced_payload_diagnostic(case, generated['text']),
                              repairFeedback=attempt.get('repairFeedback'))
                responses.append(output)
                if not correct:
                    failures.append(output)
        checkpoints.append({key: row[key] for key in ('caseId', 'model', 'repeat', 'arm', 'complete',
                                                     'worker', 'recordedAt', 'dispatchWaitMs')}
                           | {'checkpoint': checkpoint_index, 'firstCorrect': row['firstCorrect'],
                              'finalCorrect': row['finalCorrect'], 'stopReason': result['stopReason'],
                              'failure': result['failure'], 'timing': result['timing'],
                              'requestsAttempted': result['requestsAttempted']})
    summary = summarize(rows, slots)
    summary.update(audit=freeze['audit'], paired=paired_analysis(rows),
                   timing=summarize_timing([{'timing': row['result']['timing'],
                                             'status': row['result']['stopReason']} for row in rows]),
                   dispatchWaitTotalMs=sum(r['dispatchWaitMs'] for r in rows),
                   quotaEvents=read_journal(run_dir / 'events.jsonl'),
                   failureCategories=dict(Counter(category for r in failures for category in r['failureCategories']['categories'])))
    session_summary = json.loads((run_dir / 'summary.json').read_text())
    summary['sessionWallMs'] = session_summary.get('runWallMs')
    history_path = run_dir / 'session_history.json'
    session_history = json.loads(history_path.read_text()) if history_path.exists() else []
    interruptions = [session['interruption'] for session in session_history if session.get('interruption')]
    stop_path = run_dir / 'execution_stop.json'
    execution_stop = json.loads(stop_path.read_text()) if stop_path.exists() else None
    if execution_stop and execution_stop.get('interruption'):
        interruptions.append(execution_stop['interruption'])
    summary['executionStop'] = execution_stop
    summary['recordingCompleteness'] = {
        'allPhysicalRequestsKnown': not interruptions,
        'interruptionNotices': interruptions,
        'possibleUnrecordedRequestsUpperBound': sum(x['possibleUnrecordedRequestsUpperBound'] for x in interruptions),
        'tokensScope': 'Observed returned generations only; actual billing and unrecorded interrupted requests remain unknown.'}
    summary['fencedPayloads'] = {
        'responses': sum(r['fencedPayloadSemanticCorrect'] is not None for r in responses),
        'semanticallyCorrectInsideFence': sum(r['fencedPayloadSemanticCorrect'] is True for r in responses),
        'notice': 'Post-hoc diagnostic only. Markdown-wrapped outputs remain invalid JSON and failures; content is never cleaned for scoring or repair.'}
    target.mkdir(parents=True, exist_ok=True)
    for name, data in (('responses.jsonl', responses), ('checkpoints.jsonl', checkpoints), ('failures.jsonl', failures)):
        (target / name).write_text(''.join(canonical(item) + '\n' for item in data))
    for name, data in (('summary.json', summary), ('run_config.json', config)):
        (target / name).write_text(json.dumps(data, indent=2) + '\n')
    environment = run_dir / 'environment.json'
    if environment.exists():
        (target / 'environment.json').write_text(environment.read_text())
    prior_environment = run_dir / 'environment-prior.json'
    if prior_environment.exists():
        (target / 'environment-prior.json').write_text(prior_environment.read_text())
    history = run_dir / 'session_history.json'
    if history.exists():
        (target / 'session_history.json').write_text(history.read_text())
    transport_events = run_dir / 'transport_events.jsonl'
    if transport_events.exists():
        public_events = [{k: v for k, v in event.items() if k != 'headers'}
                         for event in read_journal(transport_events)]
        (target / 'transport_events.jsonl').write_text(''.join(canonical(event) + '\n' for event in public_events))
    manifest = {'freezeSha256': config['freezeSha256'], 'rawJournalSha256': sha(run_dir / 'runs.jsonl'),
                'files': {path.name: sha(path) for path in sorted(target.iterdir()) if path.name != 'manifest.json'},
                'notice': 'Only new public-source task responses. Exact final content and usage preserved; reasoning and HTTP headers omitted. Raw private traces stay in ignored results/. No previous private archives published.'}
    (target / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--out', type=Path, default=PACK / 'evidence')
    args = parser.parse_args()
    result = export(args.run_dir, args.out)
    print(json.dumps({k: result[k] for k in ('plannedSlots', 'completedSlots', 'matchedPairs')}, indent=2))
