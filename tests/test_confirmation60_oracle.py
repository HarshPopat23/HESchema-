import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('rescore60', ROOT / 'scripts/rescore_confirmation60.py')
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)
CASES = json.loads((ROOT / 'research/confirmation-60-v1/cases.json').read_text())


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['id'])
def test_reference_and_negative_control(case):
    assert oracle.correct(json.dumps(case['expected']), case)
    assert not oracle.correct('{}', case)
    bad = copy.deepcopy(case['expected'])
    family = case['family']
    if family == 'List membership':
        for choice in case['snapshot']['data']['allowed']:
            assert oracle.correct(json.dumps({'selected': choice}), case)
        bad['selected'] = '__not_a_source_choice__'
    elif family == 'Date ordering':
        bad['start'], bad['end'] = bad['end'], bad['start']
    elif family == 'Identifier matching':
        bad['requestedId'] = '__wrong_identifier__'
    elif family == 'Uniqueness':
        bad['records'][1] = copy.deepcopy(bad['records'][0])
    else:
        target = case['contract']['relationships'][0]['target'][1:]
        bad[target] += 1
    assert not oracle.correct(json.dumps(bad), case)
    if case.get('d_calc'):
        inputs = copy.deepcopy(case['expected'])
        for rule in case['d_calc']:
            inputs.pop(rule['target'][1:])
        assert oracle.correct(json.dumps(inputs), case, 'D')
        assert not oracle.correct('{}', case, 'D')


def test_strict_json():
    case = next(c for c in CASES if c['family'] == 'List membership')
    assert not oracle.correct('```json\n{}\n```', case)
    assert not oracle.correct('{"selected":"GDACS","selected":"JTWC"}', case)
    assert not oracle.correct('{"selected":NaN}', case)
