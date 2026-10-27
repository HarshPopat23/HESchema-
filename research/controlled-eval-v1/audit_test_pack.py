"""Offline audit of research inputs. This never calls an LLM or executes a tool."""
import argparse
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from heschema.context_schema import ContextError
from heschema.contracts import Contract
from heschema.experiments import _score, _task, dry_run
from heschema.schema import SchemaEngine
from heschema.validation import validate_contract


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pack', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    pack = args.pack
    cases = read_rows(pack / 'controlled_report_cases_65.jsonl')
    probes = read_rows(pack / 'controlled_validator_probes_77.jsonl')
    manifest = json.loads((pack / 'manifest.json').read_text(encoding='utf-8'))
    failures, rows, projection_checks = [], [], 0
    by_id = {case['id']: case for case in cases}
    assert len(by_id) == len(cases) == 65
    assert len({p['id'] for p in probes}) == len(probes) == 77
    for entry in (manifest['dataset'], manifest['probes']):
        assert hashlib.sha256((pack / entry['file']).read_bytes()).hexdigest() == entry['sha256']
    engine = SchemaEngine('jsonschema')
    try:
        for case in cases:
            contract, snapshot, messages, effective, projected, projection = _task(case)
            evaluation = validate_contract(case['expected'], engine, contract, snapshot)
            score = _score(evaluation, case)
            if not evaluation['accepted'] or not score['success']:
                failures.append({'id': case['id'], 'problem':'Invalid positive oracle', 'errors':evaluation['errors']})
            if evaluation['executionAuthorized'] is not False:
                failures.append({'id': case['id'], 'problem':'Unexpected execution authorization'})
            changed = copy.deepcopy(case)
            changed['expected'] = {'SCORING_ONLY_CHANGED': True}
            if _task(changed)[2] != messages:
                failures.append({'id': case['id'], 'problem':'Scoring oracle changes inference messages'})
            # These two examples are a smoke check, never an equivalence proof.
            candidate = next(p['output'] for p in probes if p.get('sourceCase') == case['id'] and p['id'].startswith('P-'))
            left = Draft202012Validator(effective, format_checker=FormatChecker())
            right = Draft202012Validator(projected, format_checker=FormatChecker())
            for value in (case['expected'], candidate):
                projection_checks += 1
                if left.is_valid(value) != right.is_valid(value):
                    failures.append({'id':case['id'], 'problem':'Projection changes example validity'})
            rows.append({'id':case['id'],'positiveAccepted':evaluation['accepted'],'oracleAgreement':score['intentAgreement'],
                         'decision':evaluation['result'],'stages':evaluation['stages'],'scope':evaluation['intentScope']})
        for probe in probes:
            source = by_id.get(probe.get('sourceCase'))
            contract = Contract(**(probe.get('contract') or source['contract']))
            snapshot = copy.deepcopy(source.get('context')) if source else None
            if probe.get('contextPatch'):
                snapshot = {**(snapshot or {}), **probe['contextPatch']}
            raw = probe['raw'] if 'raw' in probe else probe['output']
            try:
                evaluation = validate_contract(raw, engine, contract, snapshot)
            except ContextError:
                if probe.get('expectedException') != 'ContextError':
                    failures.append({'id':probe['id'], 'problem':'Unexpected ContextError'})
                continue
            if probe.get('expectedException'):
                failures.append({'id':probe['id'], 'problem':'Expected exception was absent'})
            stage = probe.get('expectedFailureStage')
            if stage == 'oracleOnly':
                if not evaluation['accepted'] or _score(evaluation, source)['intentAgreement'] is not False:
                    failures.append({'id':probe['id'], 'problem':'Wrong-source probe should pass runtime and fail hidden scoring'})
            elif stage and evaluation['stages'][stage] != 'invalid':
                failures.append({'id':probe['id'], 'problem':'Expected invalid stage', 'stage':stage,'actual':evaluation['stages']})
            if 'expectedResult' in probe and probe['expectedResult'] and evaluation['result'] != probe['expectedResult']:
                failures.append({'id':probe['id'], 'problem':'Unexpected control decision','actual':evaluation['result']})
            if 'expectedAccepted' in probe and evaluation['accepted'] != probe['expectedAccepted']:
                failures.append({'id':probe['id'], 'problem':'Unexpected control acceptance'})
            if evaluation['executionAuthorized'] is not False:
                failures.append({'id':probe['id'], 'problem':'Unexpected execution authorization'})
    finally:
        engine.close()
    estimate = dry_run(cases, repeats=3, warmup=3, repair_budgets=(1,2))
    report = {'auditType':'offline_fixture_audit','empiricalLLMEvidence':False,'cases':len(cases),'probes':len(probes),
              'families':dict(Counter(c['family'] for c in cases)),'projectionExampleChecks':projection_checks,
              'projectionClaim':'Two-example smoke checks only; no equivalence proof or backend enforcement claim.',
              'requestUpperBoundPerModel':estimate,'failures':failures,'passed':not failures,'positiveCases':rows}
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'positiveCases'},indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
