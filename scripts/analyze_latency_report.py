"""Descriptive stratification of verified latency slots, without new inference."""
import json
import math
import random
import statistics
from pathlib import Path

from rescore_confirmation60 import correct


def describe(values):
    values = sorted(values)
    return {'n': len(values), 'median': statistics.median(values),
            'p95': values[math.ceil(.95*len(values))-1], 'mean': statistics.mean(values),
            'max': values[-1], 'positiveCount': sum(v > 0 for v in values)}


def analyze(root):
    root = Path(root)
    cases = {c['id']: c for c in json.loads((root.parents[1]/'confirmation-60-v1/cases.json').read_text())}
    rows = [json.loads(p.read_text()) for p in sorted((root/'slots').glob('*.json'))]
    receipts = {p.stem:json.loads(p.read_text()) for p in (root/'requests').glob('*.json')}
    assert len(rows) == 2160
    metrics = ('serviceTotalMs', 'providerRoundTripMs', 'pacingWaitMs', 'retryWaitMs',
               'localValidationMs', 'applicationCalculationMs', 'otherMs', 'queueWaitMs', 'endToEndMs', 'activePipelineMs')
    for row in rows:
        row['project'] = cases[row['caseId']]['project']
        row['family'] = cases[row['caseId']]['family']
        chosen = [receipts[i] for i in row['requestIds']]
        row['worker'] = chosen[0]['worker']
        row['correct'] = correct(chosen[-1]['rawContent'], cases[row['caseId']], row['arm'])
        row['timing']['activePipelineMs'] = row['timing']['serviceTotalMs']-row['timing']['pacingWaitMs']-row['timing']['retryWaitMs']
    result = {}
    result['physicalRequests'] = {}
    for phase in ('initial', 'repair'):
        subset = [r for r in receipts.values() if r['phase'] == phase]
        result['physicalRequests'][phase] = {
            'n': len(subset), 'returned': sum(r['state']=='returned' for r in subset),
            'failed': sum(r['state']=='failed' for r in subset),
            'roundTripMs': describe([r['roundTripMs'] for r in subset]),
        }
    for dimension in ('project', 'family', 'worker', 'model'):
        result[dimension] = {}
        for value in sorted({r[dimension] for r in rows}):
            result[dimension][str(value)] = {}
            for arm in 'ABCD':
                subset = [r for r in rows if r[dimension] == value and r['arm'] == arm]
                if subset:
                    result[dimension][str(value)][arm] = {m:describe([r['timing'][m] for r in subset]) for m in metrics}
    projects = sorted({r['project'] for r in rows})
    result['pairedProjectBootstrap'] = {}
    for metric in ('serviceTotalMs','providerRoundTripMs','activePipelineMs'):
        result['pairedProjectBootstrap'][metric] = {}
        for left,right in [('B','A'),('C','B'),('D','C')]:
            deltas=[]
            for project in projects:
                subset=[r for r in rows if r['project']==project and (left!='D' or cases[r['caseId']].get('d_calc'))]
                means={a:statistics.mean(r['timing'][metric] for r in subset if r['arm']==a) for a in (left,right)}
                deltas.append(means[left]-means[right])
            rng=random.Random(20261024)
            samples=sorted(statistics.mean(rng.choices(deltas,k=len(deltas))) for _ in range(10000))
            result['pairedProjectBootstrap'][metric][left+'-'+right]={
                'meanDifferenceMs':statistics.mean(deltas),'descriptive95':[samples[249],samples[9749]],
                'arithmeticOnly':left=='D'}
    (root/'stratified-latency.json').write_text(json.dumps(result,indent=2)+'\n')
    print('LATENCY_STRATIFICATION_VERIFIED')


if __name__=='__main__':
    import sys
    analyze(sys.argv[1])
