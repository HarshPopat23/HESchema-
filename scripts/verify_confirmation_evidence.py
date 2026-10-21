"""Reconstruct reported outcomes from published final content, without private logs."""

import hashlib
import json
from collections import defaultdict
from pathlib import Path

from heschema.confirmation import PACK, oracle, sha, verify_freeze
from heschema.contracts import Contract
from heschema.providers import Generation
from heschema.schema import SchemaEngine
from heschema.validation import validate_contract


def verify(pack=PACK):
    pack = Path(pack)
    verify_freeze(pack)
    evidence = pack / 'evidence'
    manifest = json.loads((evidence / 'manifest.json').read_text())
    if manifest['freezeSha256'] != sha(pack / 'freeze.json'):
        raise ValueError('Evidence belongs to a different frozen pack')
    for name, expected in manifest['files'].items():
        if Path(name).name != name or sha(evidence / name) != expected:
            raise ValueError('Evidence file hash mismatch')
    cases = {c['id']: c for c in json.loads((pack / 'cases.json').read_text())}
    summary = json.loads((evidence / 'summary.json').read_text())
    protocol = json.loads((pack / 'protocol.json').read_text())
    responses = [json.loads(line) for line in (evidence / 'responses.jsonl').read_text().splitlines()]
    checkpoints = [json.loads(line) for line in (evidence / 'checkpoints.jsonl').read_text().splitlines()]
    engine = SchemaEngine()
    by_checkpoint, by_slot = defaultdict(list), defaultdict(list)

    def key(row):
        return (row['caseId'], row['model'], row['repeat'], row['arm'])

    for response in responses:
        case = cases[response['caseId']]
        if response['model'] not in protocol['models']:
            raise ValueError('Unexpected model')
        if hashlib.sha256(response['text'].encode()).hexdigest() != response['textSha256']:
            raise ValueError('Final content hash mismatch')
        if oracle(case, response['text']) != response['correct']:
            raise ValueError('Published oracle judgment differs')
        result = validate_contract(response['text'], engine, Contract(**case['contract']), case['snapshot'],
                                   generation=Generation(response['text'], metadata={'finish_reason': response['finishReason']}))
        if result['accepted'] != response['accepted'] or result['referenceSchemaValid'] != response['schemaAccepted']:
            raise ValueError('Published validation judgment differs')
        by_checkpoint[response['checkpoint']].append(response)
        by_slot[key(response)].append(response)
    latest, first = {}, {}
    for checkpoint in checkpoints:
        slot = key(checkpoint)
        returned = sorted(by_checkpoint[checkpoint['checkpoint']], key=lambda r: r['attempt'])
        for response in returned:
            if response['attempt'] == 0:
                if slot in first:
                    raise ValueError('A recorded initial generation was regenerated')
                first[slot] = response
        initial = first.get(slot)
        final = returned[-1] if returned else initial
        observed = (initial['correct'] if initial else None, final['correct'] if final else None)
        if observed != (checkpoint['firstCorrect'], checkpoint['finalCorrect']):
            raise ValueError('Checkpoint outcome is not supported by response content')
        latest[slot] = checkpoint
    completed = {k: v for k, v in latest.items() if v['complete']}
    if len(completed) != summary['completedSlots']:
        raise ValueError('Completed-slot count mismatch')
    pairs = defaultdict(set)
    for slot in completed:
        pairs[slot[:3]].add(slot[3])
    matched = {group for group, arms in pairs.items() if arms == {'full', 'compact'}}
    if len(matched) != summary['matchedPairs']:
        raise ValueError('Matched-pair count mismatch')
    for arm, metrics in summary['arms'].items():
        slots = [k for k in completed if k[:3] in matched and k[3] == arm]
        returned = [r for slot in slots for r in by_slot[slot]]
        usage_known = all(r['inputTokens'] is not None and r['outputTokens'] is not None for r in returned)
        actual = {'matchedSlots': len(slots),
                  'firstCorrect': sum(completed[k]['firstCorrect'] is True for k in slots),
                  'finalCorrect': sum(completed[k]['finalCorrect'] is True for k in slots),
                  'totalTokensIncludingEarlierCheckpoints': sum(r['inputTokens'] + r['outputTokens'] for r in returned) if usage_known else None,
                  'wrongAcceptedResponses': sum(r['accepted'] and not r['correct'] for r in returned),
                  'correctRejectedResponses': sum(not r['accepted'] and r['correct'] for r in returned),
                  'schemaOnlyWrongAcceptedResponses': sum(r['schemaAccepted'] is True and not r['correct'] for r in returned)}
        if any(metrics[k] != v for k, v in actual.items()):
            raise ValueError('Published aggregate differs from raw response evidence')
    if len(responses) != summary['returnedResponses']:
        raise ValueError('Returned response count mismatch')
    return {'verifiedResponses': len(responses), 'completedSlots': len(completed), 'matchedPairs': len(matched),
            'recordingComplete': summary['recordingCompleteness']['allPhysicalRequestsKnown']}


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
