"""Explicit second segment after host loss; never overwrite first-segment evidence."""
import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path

import latency_study as study

ROOT = study.base.ROOT
PARENT = ROOT / 'research/latency-20261024'
FIRST = PARENT / 'main'
SECOND = PARENT / 'continuation'


def identity(row):
    return tuple(row[k] for k in ('caseId', 'model', 'repeat', 'arm'))


def plan():
    manifest = json.loads((FIRST / 'manifest.json').read_text())
    for path, digest in manifest['codeHashes'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    rows = [json.loads(p.read_text()) for p in sorted((FIRST / 'slots').glob('*.json'))]
    receipts = [json.loads(p.read_text()) for p in (FIRST / 'requests').glob('*.json')]
    complete = {r['slotIndex'] for r in rows}
    assert len(complete) == len(rows) == 635
    for row in rows:
        assert identity(row) == identity(manifest['slots'][row['slotIndex']])
        study.verify_timing(row['timing'])
    pending = [r for i, r in enumerate(manifest['slots']) if i not in complete]
    incomplete = sorted({r['slotIndex'] for r in receipts} - complete)
    assert len(pending) == 1525 and len(incomplete) == 5
    assert not ({identity(r) for r in rows} & {identity(r) for r in pending})
    provenance = {
        'reason': 'Execution host reset; running process and temporary environment lost.',
        'originalCompleted': len(rows), 'remaining': len(pending),
        'interruptedOriginalIndices': incomplete,
        'excludedPrimaryGroups': [manifest['slots'][i] for i in incomplete],
        'originalManifestSha256': hashlib.sha256((FIRST/'manifest.json').read_bytes()).hexdigest(),
        'originalEvidenceHashes': {str(p.relative_to(FIRST)): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for folder in ('slots','requests') for p in sorted((FIRST/folder).glob('*.json'))},
        'pendingSchedule': pending,
        'limitations': ['Separate host/dependency epoch; segment-relative queue clocks.',
                       'Five interrupted slots restarted explicitly, not classified as successful original responses.',
                       'Exclude entire case/model/repeat groups containing restarted slots from primary comparison.'],
    }
    print('CONTINUATION_PLAN_VERIFIED')
    return provenance


def verify():
    provenance = json.loads((PARENT/'continuation-provenance.json').read_text())
    for rel, digest in provenance['originalEvidenceHashes'].items():
        assert hashlib.sha256((FIRST/rel).read_bytes()).hexdigest() == digest, rel
    study.verify(SECOND)
    first = [json.loads(p.read_text()) for p in sorted((FIRST/'slots').glob('*.json'))]
    receipts = {p.stem: json.loads(p.read_text()) for p in (FIRST/'requests').glob('*.json')}
    for row in first:
        selected = [receipts[i] for i in row['requestIds']]
        assert all(r['state']=='returned' and r['slotIndex']==row['slotIndex'] for r in selected)
        attempts = [r for r in receipts.values() if r['slotIndex']==row['slotIndex']]
        assert all(r['state'] in ('returned','failed') for r in attempts)
        assert abs(sum(r['roundTripMs'] for r in attempts)-row['timing']['providerRoundTripMs']) < .01
    second = [json.loads(p.read_text()) for p in sorted((SECOND/'slots').glob('*.json'))]
    original = json.loads((FIRST/'manifest.json').read_text())['slots']
    assert len(first)+len(second) == 2160
    assert len({identity(r) for r in first+second}) == 2160
    assert {identity(r) for r in first+second} == {identity(r) for r in original}
    print('SEGMENTED_LATENCY_VERIFIED')


if __name__ == '__main__':
    if sys.argv[1] == 'plan':
        plan()
    elif sys.argv[1] == 'verify':
        verify()
    elif sys.argv[1] == 'run':
        provenance = plan()
        target = PARENT/'continuation-provenance.json'
        assert not target.exists() and not (SECOND/'manifest.json').exists()
        study.persist(target, provenance)
        keys = Path(os.environ['H60_CREDENTIAL_FILE']).read_text().splitlines()
        assert len(keys)==len(set(keys))==9
        study.base.build_schedule = lambda cases, seed: provenance['pendingSchedule']
        asyncio.run(study.execute(SECOND, keys))
    else:
        raise SystemExit('Use plan, run, or verify')
