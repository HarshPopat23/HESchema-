"""Third session; reuse intact initial responses and disclose interrupted timers."""
import asyncio
import hashlib
import inspect
import json
import os
import sys
from pathlib import Path

import latency_study as study

PARENT = study.base.ROOT / 'research/latency-20261024'
THIRD = PARENT/'completion'


def identity(row):
    return tuple(row[k] for k in ('caseId','model','repeat','arm'))


def plan():
    schedule = json.loads((PARENT/'main/manifest.json').read_text())['slots']
    completed = set()
    candidates = {}
    frozen = {}
    for segment in ('main','continuation'):
        directory = PARENT/segment
        manifest = json.loads((directory/'manifest.json').read_text())
        for rel, digest in manifest['codeHashes'].items():
            assert hashlib.sha256((study.base.ROOT/rel).read_bytes()).hexdigest()==digest
        for p in (directory/'slots').glob('*.json'):
            row = json.loads(p.read_text())
            key = identity(row)
            assert key not in completed
            completed.add(key)
        for p in (directory/'requests').glob('*.json'):
            row = json.loads(p.read_text())
            if row['state']=='returned' and row['phase']=='initial':
                candidates[identity(row['slot'])] = row
        for p in directory.rglob('*.json'):
            frozen[str(p.relative_to(PARENT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    remaining = [r for r in schedule if identity(r) not in completed]
    assert len(completed)==1315 and len(remaining)==845
    saved = {i:candidates[identity(row)] for i,row in enumerate(remaining) if identity(row) in candidates}
    assert len(saved)==3
    assert not (completed & {identity(r) for r in remaining})
    print('FINAL_CONTINUATION_PLAN_VERIFIED')
    return remaining,saved,frozen


def generation_source():
    # Transform the exact frozen executor, leaving its original file and behavior intact.
    source = inspect.getsource(study.execute)
    substitutions = [
        ('async def execute(out, keys, pilot=False, interval=15):',
         'async def execute(out, keys, pilot=False, interval=15, saved=None):'),
        ('returned = []\n                    diagnostic = \'\'\n                    for phase in (\'initial\', \'repair\'):',
         '''returned = [saved[number]] if saved and number in saved else []
                    diagnostic = ''
                    phases = ('initial', 'repair')
                    if returned:
                        before = time.perf_counter()
                        accepted, diagnostic, calculation = detector(returned[0]['rawContent'], slot['arm'], case, contract, engine)
                        evaluation = (time.perf_counter()-before)*1000
                        times['applicationCalculationMs'] += calculation
                        times['localValidationMs'] += evaluation-calculation
                        phases = () if accepted or not returned[0]['rawContent'] else ('repair',)
                    for phase in phases:'''),
        ("'accepted': accepted, 'timing': timing,",
         "'accepted': accepted, 'timing': timing, 'resumedInitialId': saved[number]['id'] if saved and number in saved else None,"),
    ]
    for old,new in substitutions:
        assert source.count(old)==1, old
        source = source.replace(old,new)
    compile(source,'<explicit-third-session-executor>','exec')
    return source


async def run():
    remaining,saved,frozen = plan()
    assert not (THIRD/'manifest.json').exists()
    source = generation_source()
    provenance = {'completedBefore':1315,'remainingAtStart':845,'previousEvidenceHashes':frozen,
                  'reusedInitials':{str(i):r['id'] for i,r in saved.items()},
                  'schedule':remaining,'executedFunctionSha256':hashlib.sha256(source.encode()).hexdigest(),
                  'scope':'Separate session with new credentials. Reused-initial slots measure resumed processing only and are excluded with their whole groups from primary latency.'}
    study.persist(PARENT/'completion-provenance.json',provenance)
    namespace = dict(vars(study))
    exec(source,namespace)
    study.base.build_schedule = lambda cases,seed: remaining
    keys = Path(os.environ['H60_CREDENTIAL_FILE']).read_text().splitlines()
    assert len(keys)==len(set(keys))==9
    await namespace['execute'](THIRD,keys,saved=saved)


if __name__=='__main__':
    if sys.argv[1]=='plan':
        plan()
        generation_source()
    elif sys.argv[1]=='run':
        asyncio.run(run())
    else:
        raise SystemExit('Use plan or run')
