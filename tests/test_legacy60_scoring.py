"""All H60 arms score reference and alternative answers independently of detectors."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('legacy60', ROOT / 'scripts/run_60_tasks_experiment.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
CASES = json.loads((ROOT / 'research/confirmation-60-v1/cases.json').read_text())


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['id'])
@pytest.mark.parametrize('arm', list('ABCD'))
def test_legacy_runner_uses_independent_oracle(case, arm, monkeypatch):
    # Deliberately untrustworthy detector: independent correctness must ignore it.
    result = {'accepted': False, 'success': False, 'errors': [], 'parsed': {}}
    monkeypatch.setattr(runner, 'validate_contract', lambda *args: result)
    monkeypatch.setattr(runner, 'validate_with_calculations', lambda *args: result)
    _, contract = runner.build_messages_for_arm(case, arm)
    raw = dict(case['expected'])
    if arm == 'D' and case.get('d_calc'):
        for rule in case['d_calc']:
            raw.pop(rule['target'][1:])
    evaluated = runner.evaluate_attempt(json.dumps(raw), arm, case, contract, None)
    assert evaluated['oracleCorrect']
    if case['family'] == 'List membership':
        for choice in case['snapshot']['data']['allowed']:
            assert runner.evaluate_attempt(json.dumps({'selected': choice}), arm, case, contract, None)['oracleCorrect']
    monkeypatch.setattr(runner, 'validate_contract', lambda *args: {**result, 'accepted': True, 'success': True})
    monkeypatch.setattr(runner, 'validate_with_calculations', lambda *args: {**result, 'accepted': True, 'success': True})
    assert not runner.evaluate_attempt('{}', arm, case, contract, None)['oracleCorrect']


def test_resume_rescores_saved_membership_answers(tmp_path):
    case = next(c for c in CASES if c['family'] == 'List membership')
    row = dict(caseId=case['id'], model='model', repeat=0, arm='B',
               rawResponse1=json.dumps(case['expected']), repairAttempted=False,
               firstCorrect=False, finalCorrect=False, finalAccepted=True, falseAcceptance=True)
    path = tmp_path / 'runs.jsonl'
    path.write_text(json.dumps(row) + '\n')
    saved = list(runner.load_existing_runs(path, {case['id']: case}).values())[0]
    assert saved['firstCorrect'] and saved['finalCorrect']
    assert not saved['falseAcceptance']
    del row['rawResponse1']
    path.write_text(json.dumps(row) + '\n')
    with pytest.raises(ValueError, match='raw evidence'):
        runner.load_existing_runs(path, {case['id']: case})
