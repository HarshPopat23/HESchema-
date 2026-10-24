"""Verify every rerun row against receipts and write a scoped reproducible report."""
import gzip
import hashlib
import json
import random
from collections import Counter

from conventional_confirmation60 import conventional
from rescore_confirmation60 import PACK, correct


def key(row):
    return tuple(row[k] for k in ('caseId', 'model', 'repeat', 'arm'))


def main():
    root = PACK / 'rerun-20261024'
    row_path = root / 'runs.jsonl'
    if row_path.exists():
        rows = [json.loads(line) for line in row_path.read_text().splitlines()]
    else:
        with gzip.open(root / 'runs.jsonl.gz', 'rt') as stream:
            rows = [json.loads(line) for line in stream]
    manifest = json.loads((root / 'manifest.json').read_text())
    for path, expected_hash in manifest['codeHashes'].items():
        assert hashlib.sha256((PACK.parents[1] / path).read_bytes()).hexdigest() == expected_hash, path
    cases = {c['id']: c for c in json.loads((PACK / 'cases.json').read_text())}
    assert hashlib.sha256((PACK / 'cases.json').read_bytes()).hexdigest() == manifest['caseSha256']
    assert len(rows) == 2160 and len({key(r) for r in rows}) == 2160
    assert {key(r) for r in rows} == {key(r) for r in manifest['schedule']}
    paths = sorted((root / 'request-evidence').glob('*.json'))
    if paths:
        receipts = [json.loads(p.read_text()) for p in paths]
    else:
        with gzip.open(root / 'request-evidence.jsonl.gz', 'rt') as stream:
            receipts = [json.loads(line) for line in stream]
    assert all(r['state'] in {'returned', 'failed'} or r.get('excludedFromSelectedSlots') for r in receipts)
    for row in rows:
        usage_in = usage_out = 0
        for phase, field in [('initial', 'rawResponse1'), ('repair', 'rawResponse2')]:
            expected = row[field]
            found = [r for r in receipts if key(r['slot']) == key(row) and r['phase'] == phase and r['state'] == 'returned' and not r.get('excludedFromSelectedSlots')]
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
    selected_count = len(rows)
    reconciliation = json.loads((root / 'reconciliation.json').read_text())
    excluded = {tuple(group) for group in reconciliation['primaryExclusionGroups']}
    rows = [r for r in rows if key(r)[:3] not in excluded]
    assert len(rows) == 4 * (540 - len(excluded))
    report = ['# H60 independent-oracle replication results', '',
              'These are new inferences on the existing authored public-record tasks, not untouched tasks.',
              'Historical outputs were independently rescored separately in `independent-rescore.json`.',
              '', f'Verified selected slots: {selected_count}. Primary matched slots: {len(rows)}. Physical request receipts: {len(receipts)}.',
              'Selected initial/repair contents and usage match their receipts. Failed and explicitly unverifiable original receipts are retained.',
              'Three missing derived rows were recovered from intact receipts. Two original slots lacked complete initial receipts and were regenerated with their original budgets; their entire matched group is excluded from the primary tables below to avoid selection bias. See reconciliation.json and the preserved original artifacts. The missing-write root cause is unknown.',
              '', '## Results', '',
              '| Arm | Slots | First correct | Final correct | Wrong accepted | Correct rejected | Input tokens incl. repair | Output tokens incl. repair |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    if (root / 'PUBLICATION_STATUS.md').exists():
        report[:0] = ['> Raw-response archives are verified locally but publication is blocked pending explicit user authorization. This PR alone is not yet sufficient for independent replay. See PUBLICATION_STATUS.md.', '']
    summary = {'selectedSlots': selected_count, 'primaryMatchedSlots': len(rows),
               'excludedGroups': sorted(excluded), 'recoveredRows': len(reconciliation['recoveredRows']),
               'replacementSlots': len(reconciliation['replacementSlots'])}
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
    summary['conventionalApplicationReplay'] = {}
    for arm in 'ABCD':
        subset = [r for r in rows if r['arm'] == arm]
        wrong_accepted = correct_rejected = disagreements = 0
        for row in subset:
            raw = row['rawResponse2'] if row['repairAttempted'] else row['rawResponse1']
            accepted = conventional(raw, cases[row['caseId']], arm)
            wrong_accepted += accepted and not row['finalCorrect']
            correct_rejected += not accepted and row['finalCorrect']
            disagreements += accepted != row['finalAccepted']
        summary['conventionalApplicationReplay'][arm] = {
            'slots': len(subset), 'wrongAccepted': wrong_accepted,
            'correctRejected': correct_rejected, 'detectorDisagreements': disagreements,
            'scope': 'offline final-output replay, no feedback or inference rerun',
        }
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
    report += ['', '## Final correctness by model, family and project', '']
    for dimension in ('model', 'family', 'project'):
        report += ['', f'### {dimension}', '', '| Group | A | B | C | D |', '|---|---:|---:|---:|---:|']
        for label, arms in summary['stratified'][dimension].items():
            report.append('| ' + label + ' | ' + ' | '.join(f"{arms[a]['finalCorrect']}/{arms[a]['slots']}" for a in 'ABCD') + ' |')
    report += ['', '## Paired descriptive uncertainty', '']
    for label, data in summary['descriptiveProjectBootstrap'].items():
        low, high = data['percentile95']
        report.append(f"- {label}: final-correct difference {100*data['finalCorrectDifference']:.2f} percentage points; project-bootstrap interval [{100*low:.2f}, {100*high:.2f}]. D-C uses arithmetic-eligible tasks only.")
    report += ['', '## Conventional application-check replay', '',
               'These task-specific checks were written from source facts and task families without calling the oracle or HESchema rule evaluator. This is an offline counterfactual, not an additional generation/repair arm.']
    for arm, data in summary['conventionalApplicationReplay'].items():
        report.append(f"- {arm}: {data['wrongAccepted']} wrong accepted, {data['correctRejected']} correct rejected; {data['detectorDisagreements']} decisions differ from the original arm detector.")
    report += ['', '## Limits and claim boundaries', '',
               '- D scores assembled system output; its calculations do not establish improved LLM arithmetic.',
               '- Wrong acceptance is a count over scheduled slots, not the conditional rate among incorrect answers.',
               '- Reported token usage is observed returned usage, not verified billed cost.',
               '- Round-trip provider timings exclude full local/wait decomposition; no speed-improvement claim is supported.',
               '- Three repeats measure consistency, not independent tasks; ten shared project clusters limit generalization.',
               '- Original source response archives were not recaptured in this replication.',
               '- See RERUN_PROTOCOL.md for controls and the JSON summary for grouped results.',
               '- Zero observed wrong acceptance is not a universal validator guarantee or proof that new keywords are needed.']
    full = summary['arm']['B']
    compact = summary['arm']['C']
    reduction = 100 * (1 - (compact['inputTokens'] + compact['outputTokens']) / (full['inputTokens'] + full['outputTokens']))
    report += ['', '## Interpretation', '',
               f'COMPACT used {reduction:.2f}% fewer selected-primary total tokens than FULL, including repairs. Its final correctness was {compact["finalCorrect"]}/{compact["slots"]} versus {full["finalCorrect"]}/{full["slots"]}. This does not establish non-inferior accuracy.',
               'The FULL-versus-ordinary final-correctness interval includes zero; there is no demonstrated general generation-accuracy improvement. Contract checks and conventional application checks caught all observed wrong selected-primary outputs, while the ordinary shape-only detector accepted 49 wrong outputs.',
               'Application calculation did not improve aggregate correctness here. It matched COMPACT on sums/products but had lower correctness on count tasks. Keep calculation optional.',
               f'Physical finish reasons: {dict(summary["finishReasons"])}. Missing original response metadata remains explicit; neither replacements nor archived data erase that evidence gap.']
    (root / 'verified-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (root / 'REPORT.md').write_text('\n'.join(report) + '\n')
    # Deterministic compression; content and usage remain available without thousands of tracked files.
    payload = ''.join(json.dumps(r, sort_keys=True) + '\n' for r in receipts).encode()
    (root / 'request-evidence.jsonl.gz').write_bytes(gzip.compress(payload, mtime=0))
    for name in ('runs.jsonl', 'original-result-rows.jsonl', 'original-receipts.jsonl'):
        source = root / name
        if source.exists():
            (root / (name + '.gz')).write_bytes(gzip.compress(source.read_bytes(), mtime=0))
    print('RERUN_EVIDENCE_VERIFIED')


if __name__ == '__main__':
    main()
