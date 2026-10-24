"""Recover derived rows from intact receipts; explicitly replace unverifiable slots.

Original rows/receipts are archived before changes. Replacement groups are
excluded from the primary matched comparison to avoid outcome-selection bias.
"""
import asyncio
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import run_60_tasks_experiment as base
from rescore_confirmation60 import PACK, correct
from run_confirmation60_verified import RecordedClient

from heschema.schema import SchemaEngine
from heschema.study_evidence import atomic_json


def key(row):
    return tuple(row[k] for k in ('caseId', 'model', 'repeat', 'arm'))


async def main():
    root = PACK / 'rerun-20261024'
    marker = root / 'reconciliation.json'
    if marker.exists():
        raise RuntimeError('Already reconciled; inspect evidence instead of repeating inference')
    raw = (root / 'runs.jsonl').read_bytes()
    (root / 'original-result-rows.jsonl').write_bytes(raw)
    rows = [json.loads(line) for line in raw.splitlines()]
    receipts = [json.loads(p.read_text()) for p in (root / 'request-evidence').glob('*.json')]
    (root / 'original-receipts.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in receipts))
    cases = {c['id']: c for c in json.loads((PACK / 'cases.json').read_text())}
    schedule = json.loads((root / 'manifest.json').read_text())['schedule']
    engine = SchemaEngine()
    recovered, replacements = [], []

    def row_from(slot, returns, provenance):
        case = cases[slot['caseId']]
        _, contract = base.build_messages_for_arm(case, slot['arm'])
        first = returns['initial']
        repair = returns.get('repair')
        evaluated = [base.evaluate_attempt(r['rawContent'], slot['arm'], case, contract, engine) for r in (first, repair) if r]
        first_correct = correct(first['rawContent'], case, slot['arm'])
        last = repair or first
        final_correct = correct(last['rawContent'], case, slot['arm'])
        return {**slot, 'project': case['project'], 'family': case['family'], 'worker': first['worker'],
                'firstAccepted': evaluated[0]['accepted'], 'firstCorrect': first_correct,
                'finalAccepted': evaluated[-1]['accepted'], 'finalCorrect': final_correct,
                'falseAcceptance': bool(evaluated[-1]['accepted'] and not final_correct),
                'repairAttempted': repair is not None,
                'totalInputTokens': sum(r['usage']['prompt_tokens'] for r in returns.values()),
                'totalOutputTokens': sum(r['usage']['completion_tokens'] for r in returns.values()),
                'latency1Ms': first['providerMs'], 'latency2Ms': repair['providerMs'] if repair else None,
                'rawResponse1': first['rawContent'], 'rawResponse2': repair['rawContent'] if repair else None,
                'recordedAt': datetime.now(timezone.utc).isoformat(), 'rowProvenance': provenance}

    seen = {key(r) for r in rows}
    for slot in schedule:
        if key(slot) not in seen:
            found = {r['phase']: r for r in receipts if key(r['slot']) == key(slot) and r['state'] == 'returned'}
            assert 'initial' in found
            row = row_from(slot, found, 'recovered_from_saved_provider_receipts')
            assert row['firstAccepted'] or 'repair' in found
            rows.append(row)
            recovered.append(slot)

    incomplete = [r for r in receipts if r['state'] == 'started']
    keys = Path(os.environ['H60_CREDENTIAL_FILE']).read_text().splitlines()
    for receipt in incomplete:
        slot = receipt['slot']
        old = next(r for r in rows if key(r) == key(slot))
        for r in receipts:
            if key(r['slot']) == key(slot):
                r['excludedFromSelectedSlots'] = True
                r['exclusionReason'] = 'Original initial provider receipt incomplete; group excluded from primary comparisons'
                atomic_json(root / 'request-evidence' / (r['id'] + '.json'), r)
        client = RecordedClient(keys[receipt['worker']], receipt['worker'])
        client.slot = slot
        messages, contract = base.build_messages_for_arm(cases[slot['caseId']], slot['arm'])
        first = await client.generate(messages, slot['model'])
        decision = base.evaluate_attempt(first['text'], slot['arm'], cases[slot['caseId']], contract, engine)
        if not decision['accepted']:
            await asyncio.sleep(15)
            await client.generate(base.build_repair_message(messages, first['text'], decision['diagnostics']), slot['model'])
        await client.close()
        fresh = [json.loads(p.read_text()) for p in (root / 'request-evidence').glob('*.json')]
        found = {r['phase']: r for r in fresh if key(r['slot']) == key(slot) and r['state'] == 'returned' and not r.get('excludedFromSelectedSlots')}
        rows.remove(old)
        rows.append(row_from(slot, found, 'replacement_of_unverifiable_original_slot'))
        replacements.append({'slot': slot, 'originalRow': old, 'incompleteReceipt': receipt['id']})
    with (root / 'runs.jsonl').open('w') as stream:
        for row in rows:
            stream.write(json.dumps(row) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    atomic_json(marker, {'originalRowsSha256': hashlib.sha256(raw).hexdigest(),
                         'recoveredRows': recovered, 'replacementSlots': replacements,
                         'primaryExclusionGroups': sorted({tuple(x['slot'][k] for k in ('caseId', 'model', 'repeat')) for x in replacements}),
                         'limitations': 'Root cause of missing writes is not established; original artifacts retained. No successful original slot was selectively regenerated.'})
    engine.close()
    print('RECONCILIATION_RECORDED')


if __name__ == '__main__':
    asyncio.run(main())
