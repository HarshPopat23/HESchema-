"""Verify every rerun row against receipts and write a scoped reproducible report."""
import gzip
import hashlib
import json
import random
from collections import Counter

from rescore_confirmation60 import PACK, correct


def key(row):
    return tuple(row[k] for k in ('caseId', 'model', 'repeat', 'arm'))


def main():
    root = PACK / 'rerun-20261024'
    rows = [json.loads(line) for line in (root / 'runs.jsonl').read_text().splitlines()]
    manifest = json.loads((root / 'manifest.json').read_text())
    cases = {c['id']: c for c in json.loads((PACK / 'cases.json').read_text())}
    assert hashlib.sha256((PACK / 'cases.json').read_bytes()).hexdigest() == manifest['caseSha256']
    assert len(rows) == 2160 and len({key(r) for r in rows}) == 2160
    assert {key(r) for r in rows} == {key(r) for r in manifest['schedule']}
    receipts = [json.loads(p.read_text()) for p in sorted((root / 'request-evidence').glob('*.json'))]
    assert all(r['state'] in {'returned', 'failed'} for r in receipts)
    for row in rows:
        usage_in = usage_out = 0
        for phase, field in [('initial', 'rawResponse1'), ('repair', 'rawResponse2')]:
            expected = row[field]
            found = [r for r in receipts if key(r['slot']) == key(row) and r['phase'] == phase and r['state'] == 'returned']
            assert len(found) == int(expected is not None)
            if found:
                assert found[0]['rawContent'] == expected
                assert found[0]['responseId'] and found[0]['resolvedModel']
                usage_in += found[0]['usage']['prompt_tokens']
                usage_out += found[0]['usage']['completion_tokens']
        assert usage_in == row['totalInputTokens'] and usage_out == row['totalOutputTokens']
        case = cases[row['caseId']]
        assert correct(row['rawResponse1'], case, row['arm']) == row['firstCorrect']
        final = row['rawResponse2'] if row['repairAttempted'] else row['rawResponse1']
        assert correct(final, case, row['arm']) == row['finalCorrect']
    report = ['# H60 independent-oracle replication results', '',
              'These are new inferences on the existing authored public-record tasks, not untouched tasks.',
              'Historical outputs were independently rescored separately in `independent-rescore.json`.',
              '', f'Verified slots: {len(rows)}. Physical request receipts: {len(receipts)}.',
              'All returned initial/repair contents and usage match their receipts. Failed requests are retained.',
              '', '## Results', '',
              '| Arm | Slots | First correct | Final correct | Wrong accepted | Correct rejected | Input tokens incl. repair | Output tokens incl. repair |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    summary = {}
    for dimension in ('arm', 'model', 'family', 'project'):
        summary[dimension] = {}
        for value in sorted({r[dimension] for r in rows}):
            subset = [r for r in rows if r[dimension] == value]
            metrics = {'slots': len(subset), 'firstCorrect': sum(r['firstCorrect'] for r in subset),
                       'finalCorrect': sum(r['finalCorrect'] for r in subset),
                       'wrongAccepted': sum(r['finalAccepted'] and not r['finalCorrect'] for r in subset),
                       'correctRejected': sum(not r['finalAccepted'] and r['finalCorrect'] for r in subset),
                       'inputTokens': sum(r['totalInputTokens'] for r in subset),
                       'outputTokens': sum(r['totalOutputTokens'] for r in subset)}
            summary[dimension][value] = metrics
            if dimension == 'arm':
                report.append('| ' + value + ' | ' + ' | '.join(str(v) for v in metrics.values()) + ' |')
    summary['physicalRequestStates'] = dict(Counter(r['state'] for r in receipts))
    summary['finishReasons'] = dict(Counter(r.get('finishReason', 'no_return') for r in receipts))
    summary['stratified'] = {}
    for dimension in ('model', 'family', 'project'):
        summary['stratified'][dimension] = {}
        for value in sorted({r[dimension] for r in rows}):
            summary['stratified'][dimension][value] = {}
            for arm in 'ABCD':
                subset = [r for r in rows if r[dimension] == value and r['arm'] == arm]
                summary['stratified'][dimension][value][arm] = {
                    'slots': len(subset), 'firstCorrect': sum(r['firstCorrect'] for r in subset),
                    'finalCorrect': sum(r['finalCorrect'] for r in subset),
                    'wrongAccepted': sum(r['falseAcceptance'] for r in subset),
                }
    summary['physicalUsage'] = {}
    for arm in 'ABCD':
        summary['physicalUsage'][arm] = {}
        for phase in ('initial', 'repair'):
            subset = [r for r in receipts if r['slot']['arm'] == arm and r['phase'] == phase and r['state'] == 'returned']
            summary['physicalUsage'][arm][phase] = {
                'returnedRequests': len(subset),
                'inputTokens': sum(r['usage']['prompt_tokens'] for r in subset),
                'outputTokens': sum(r['usage']['completion_tokens'] for r in subset),
                'roundTripMs': sum(r['providerMs'] for r in subset),
            }
    summary['descriptiveProjectBootstrap'] = {}
    projects = sorted({r['project'] for r in rows})
    for left, right in [('B', 'A'), ('C', 'B'), ('D', 'C')]:
        differences = []
        for project in projects:
            selected = [r for r in rows if r['project'] == project and (left != 'D' or cases[r['caseId']].get('d_calc'))]
            means = {a: sum(r['finalCorrect'] for r in selected if r['arm'] == a) / sum(r['arm'] == a for r in selected) for a in (left, right)}
            differences.append(means[left] - means[right])
        rng = random.Random(20261024)
        samples = sorted(sum(rng.choices(differences, k=len(projects)))/len(projects) for _ in range(10000))
        summary['descriptiveProjectBootstrap'][left+'-'+right] = {
            'finalCorrectDifference': sum(differences)/len(differences),
            'percentile95': [samples[249], samples[9749]],
            'clusters': len(projects), 'DComparisonArithmeticOnly': left == 'D',
        }
    report += ['', '## Limits and claim boundaries', '',
               '- D scores assembled system output; its calculations do not establish improved LLM arithmetic.',
               '- Wrong acceptance is a count over scheduled slots, not the conditional rate among incorrect answers.',
               '- Reported token usage is observed returned usage, not verified billed cost.',
               '- Round-trip provider timings exclude full local/wait decomposition; no speed-improvement claim is supported.',
               '- Three repeats measure consistency, not independent tasks; ten shared project clusters limit generalization.',
               '- Original source response archives were not recaptured in this replication.',
               '- See RERUN_PROTOCOL.md for controls and the JSON summary for grouped results.',
               '- Zero observed wrong acceptance is not a universal validator guarantee or proof that new keywords are needed.']
    (root / 'verified-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (root / 'REPORT.md').write_text('\n'.join(report) + '\n')
    # Deterministic compression; content and usage remain available without thousands of tracked files.
    payload = ''.join(json.dumps(r, sort_keys=True) + '\n' for r in receipts).encode()
    (root / 'request-evidence.jsonl.gz').write_bytes(gzip.compress(payload, mtime=0))
    print('RERUN_EVIDENCE_VERIFIED')


if __name__ == '__main__':
    main()
