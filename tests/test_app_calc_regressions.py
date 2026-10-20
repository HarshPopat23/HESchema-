"""Public-source controls inspired by the audit; no private provider responses are embedded."""

import asyncio
import copy
import importlib.util
from pathlib import Path

import pytest

from heschema.calculations import calculation_plan, validate_with_calculations
from heschema.contracts import Contract
from heschema.jsonio import canonical, loads
from heschema.providers import Generation
from heschema.repair import RepairLimits, coordinate, feedback_message
from heschema.schema import SchemaEngine
from heschema.validation import validate_contract

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('app_calc_audit', ROOT / 'scripts/analyze_app_calc_regressions.py')
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)
PUBLIC_CASES = {case['id']: case for case in loads(
    (ROOT / 'research/contract-main-study-v1/inputs/cases.json').read_text())}


def public_control(case_id):
    """Computed expected answers and constructed errors are not original LLM responses."""
    case = PUBLIC_CASES[case_id]
    definition = copy.deepcopy(case['contract'])
    definition['id'] = 'regression-' + case_id
    for rule in definition['relationships']:
        if rule['kind'] in {'count_equals', 'sum_items_equals'}:
            rule['compute'] = 'application'
    contract = Contract(**definition)
    document = copy.deepcopy(case['expected_output'])
    for rule in calculation_plan(contract):
        document.pop(rule['target'][1:])
    return contract, case['context'], document


def test_historical_repair_summary_counts_slots_once_and_uses_saved_correctness():
    def row(mode, codes, correct):
        return {'slot': {'mode': mode}, 'first': {'diagnostics': [{'code': code} for code in codes]},
                'repair': {}, 'final': {'correct': correct}}
    controls = [row('FULL', ['json_parse', 'json_parse'], True),
                row('FULL', ['sum_items_equals'], False),
                row('COMPACT', ['schema_const', 'sum_items_equals'], False)]
    assert AUDIT.repair_category_summary(controls) == {
        'FULL': {'json_parse': {'attempts': 1, 'recovered': 1},
                 'sum_items_equals': {'attempts': 1, 'recovered': 0}},
        'COMPACT': {'schema_const+sum_items_equals': {'attempts': 1, 'recovered': 0}}}


@pytest.mark.parametrize('case_id', ['CR-001', 'CR-004', 'PYPI-001'])
@pytest.mark.parametrize('defect', ['extra_brace', 'bad_record_delimiter'])
def test_constructed_syntax_errors_reach_feedback_without_accepting_a_json_prefix(case_id, defect):
    contract, context, document = public_control(case_id)
    text = canonical(document)
    text = text + '}' if defect == 'extra_brace' else text.replace('},{', '},"{', 1)
    engine = SchemaEngine()
    try:
        result = validate_with_calculations(text, engine, contract, context)
    finally:
        engine.close()
    error = result['errors'][0]
    assert error['code'] == 'JSON_INVALID'
    assert error['jsonError'] == AUDIT.syntax_probe(text)
    feedback = loads(feedback_message([error]).split(': ', 1)[1])[0]
    assert feedback['jsonError']['offset'] == error['jsonError']['offset']
    assert 'preserve approved field values' in feedback['repairHint']
    assert not result['accepted'] and result['calculation']['values'] == []


@pytest.mark.parametrize('case_id', ['CR-001', 'PYPI-001'])
@pytest.mark.parametrize('mutation', ['change_value', 'drop_nested_property', 'reverse_records'])
def test_arithmetic_cannot_hide_corrupted_copied_fields_from_public_sources(case_id, mutation, monkeypatch):
    contract, context, document = public_control(case_id)
    field = 'authors' if case_id == 'CR-001' else 'files'
    if mutation == 'change_value':
        document[field][0]['given' if field == 'authors' else 'filename'] = 'synthetic-negative-control'
    elif mutation == 'drop_nested_property':
        document[field][0].pop('role' if field == 'authors' else 'digests')
    else:
        document[field].reverse()
    def forbidden(*args):
        raise AssertionError('Corrupt copied inputs must be rejected before calculation')
    monkeypatch.setattr('heschema.calculations.calculation_value', forbidden)
    engine = SchemaEngine()
    try:
        result = validate_with_calculations(canonical(document), engine, contract, context)
    finally:
        engine.close()
    assert not result['accepted'] and result['calculation']['status'] == 'blocked'


def test_constructed_filename_error_cannot_hide_behind_unchanged_sizes(monkeypatch):
    contract, context, document = public_control('WF-007')
    sizes = [item['sizeInBytes'] for item in document['files']]
    document['files'][-1]['id'] = 'synthetic-negative-control'
    assert [item['sizeInBytes'] for item in document['files']] == sizes
    def forbidden(*args):
        raise AssertionError('A matching total must not hide a copied filename error')
    monkeypatch.setattr('heschema.calculations.calculation_value', forbidden)
    engine = SchemaEngine()
    try:
        result = validate_with_calculations(canonical(document), engine, contract, context)
    finally:
        engine.close()
    assert not result['accepted'] and result['calculation']['sourceValid'] is False
    assert result['errors'][0]['code'] == 'CONTEXT_MISMATCH'


def test_replaying_an_identical_malformed_repair_does_not_fabricate_a_recovery():
    contract, context, document = public_control('CR-001')
    initial = canonical(document) + '}'
    seen = []
    async def generate(messages, attempt):
        seen.append(copy.deepcopy(messages))
        return Generation(initial, metadata={'finish_reason': 'stop'})
    engine = SchemaEngine()
    try:
        result = asyncio.run(coordinate(
            generate, lambda g: validate_with_calculations(g.text, engine, contract, context, generation=g),
            [{'role': 'user', 'content': 'Return the approved metadata.'}], limits=RepairLimits(1),
            first_generation=Generation(initial, metadata={'finish_reason': 'stop'})))
    finally:
        engine.close()
    assert not result['finalEvaluation']['accepted'] and result['stopReason'] == 'exhausted'
    assert [attempt['generation']['text'] for attempt in result['attempts']] == [initial, initial]
    assert 'jsonError' in seen[0][-1]['content'] and 'repairHint' in seen[0][-1]['content']


@pytest.mark.parametrize('text', ['{"n":1,"n":2}', '{"n":NaN}', '{"n":1e400}'])
def test_non_syntax_rejections_do_not_invent_parser_locations(text):
    engine = SchemaEngine()
    try:
        result = validate_contract(text, engine, Contract('json', '1', {}))
    finally:
        engine.close()
    assert not result['accepted'] and result['errors'][0]['code'] == 'JSON_INVALID'
    assert 'jsonError' not in result['errors'][0]
