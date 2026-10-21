"""Labelled acceptance controls, not new LLM outputs or empirical failure rates."""

import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from heschema.calculations import validate_with_calculations
from heschema.context_schema import ContextError
from heschema.contracts import Contract
from heschema.jsonio import loads
from heschema.providers import Generation
from heschema.rules import KINDS
from heschema.validation import envelope, validate_contract

PUBLIC_CASES = {c['id']: c for c in loads((Path(__file__).resolve().parents[1] /
    'research/contract-main-study-v1/inputs/cases.json').read_text(encoding='utf-8'))}


def approved(data=None, pointers=None, **changes):
    return {'id': 'source', 'version': 1, 'confirmed': True,
            'data': {'owner': 'control'} if data is None else data,
            'approvedPointers': ['/owner'] if pointers is None else pointers, 'facts': [], **changes}


def check(engine, contract, output, context):
    before = copy.deepcopy((contract.as_dict(), output, context))
    result = validate_contract(output, engine, contract, context)
    assert (contract.as_dict(), output, context) == before
    assert result['executionAuthorized'] is False
    return result


def station_choice():
    # Researcher-authored choice task using actual preserved public station IDs.
    ids = [s['station_id'] for s in PUBLIC_CASES['GBFS-001']['context']['data']['stations'][:2]]
    contract = Contract('station-choice-control', '1', {'type': 'object', 'properties': {
        'stationId': {'type': 'string', 'minLength': 1},
        'travellers': {'type': 'integer', 'minimum': 1, 'maximum': 8},
        'note': {'type': 'string', 'maxLength': 40}},
        'required': ['stationId', 'travellers'], 'additionalProperties': False},
        bindings=[{'instanceLocation': '/stationId', 'contextLocation': '/allowedIds', 'keyword': 'enum'}])
    return contract, approved({'allowedIds': ids}, ['/allowedIds']), ids


@pytest.mark.parametrize('station_index', [0, 1])
@pytest.mark.parametrize('travellers', [1, 8])
@pytest.mark.parametrize('note', [None, 'Either approved station is valid.'])
def test_multiple_valid_public_source_choices_are_not_rejected_for_differing_from_one_gold(
        validation_engine, station_index, travellers, note):
    contract, context, ids = station_choice()
    output = {'stationId': ids[station_index], 'travellers': travellers}
    if note is not None:
        output['note'] = note
    result = check(validation_engine, contract, output, context)
    assert result['accepted'] and result['success'] and not result['errors']


@pytest.mark.parametrize('field,value,stage', [
    ('stationId', 'constructed-invalid-station', 'context'),
    ('stationId', '', 'originalSchema'), ('travellers', 0, 'originalSchema'),
    ('travellers', 9, 'originalSchema'), ('travellers', True, 'originalSchema'),
    ('travellers', 1.5, 'originalSchema'), ('note', 'x' * 41, 'originalSchema'),
    ('unexpected', 1, 'originalSchema'),
])
def test_public_choice_neighbours_and_source_corruptions_fail_at_the_expected_stage(validation_engine, field, value, stage):
    contract, context, ids = station_choice()
    result = check(validation_engine, contract, {'stationId': ids[0], 'travellers': 1, field: value}, context)
    assert not result['accepted'] and result['stages'][stage] == 'invalid'
    assert result['stages']['relationships'] == 'not_evaluated'


@pytest.mark.parametrize('case_id', ['WF-001', 'USGS-001', 'GBFS-001', 'CR-001', 'PYPI-001'])
@pytest.mark.parametrize('style', ['pretty', 'reversed_keys', 'unicode'])
def test_public_answers_accept_equivalent_json_serializations(validation_engine, case_id, style):
    case = PUBLIC_CASES[case_id]
    output = case['expected_output']
    text = (json.dumps(output, indent=3) if style == 'pretty' else
            json.dumps(dict(reversed(list(output.items())))) if style == 'reversed_keys' else
            json.dumps(output, ensure_ascii=False))
    result = check(validation_engine, Contract(**case['contract']), text, case['context'])
    assert result['accepted'] and result['success']


@pytest.mark.parametrize('value,valid', [(1, True), (1.0, True), (8, True), (8.0, True),
    (0, False), (9, False), (1.5, False), (True, False), (False, False), (None, False)])
@pytest.mark.parametrize('keyword', ['minimum', 'maximum'])
def test_numeric_projection_preserves_inclusive_boundaries_and_original_type(validation_engine, value, valid, keyword):
    contract = Contract('bound-control', '1', {'type': 'object', 'properties': {
        'n': {'type': 'integer', 'minimum': 0 if keyword == 'minimum' else 1,
              'maximum': 8 if keyword == 'minimum' else 10}}, 'required': ['n']},
        bindings=[{'instanceLocation': '/n', 'contextLocation': '/bound', 'keyword': keyword}])
    result = check(validation_engine, contract, {'n': value}, approved({'bound': 1 if keyword == 'minimum' else 8}, ['/bound']))
    assert result['accepted'] is valid
    if (keyword == 'minimum' and value == 0 and type(value) is int) or (keyword == 'maximum' and value == 9):
        assert result['stages']['originalSchema'] == 'valid' and result['stages']['context'] == 'invalid'


@pytest.mark.parametrize('schema,good,bad', [
    ({'type': 'string', 'minLength': 1, 'maxLength': 2}, ['é', '😀', 'ab'], ['', 'abc']),
    ({'type': 'array', 'minItems': 1, 'maxItems': 2}, [[1], [1, 2]], [[], [1, 2, 3]]),
    ({'type': 'number', 'exclusiveMinimum': 1, 'exclusiveMaximum': 3}, [1.5, 2], [1, 3]),
    ({'type': 'object', 'required': ['x'], 'additionalProperties': False,
      'properties': {'x': {'type': ['integer', 'null']}}}, [{'x': None}, {'x': 0}], [{}, {'x': 0, 'extra': 1}]),
])
def test_standard_schema_boundary_sets_allow_valid_alternatives(validation_engine, schema, good, bad):
    contract = Contract('schema-control', '1', schema)
    for output in good:
        result = check(validation_engine, contract, json.dumps(output), None)
        assert result['accepted'] and result['result'] == 'NOT_CHECKED'
        assert not result['success'] and result['semanticValid'] is None
    for output in bad:
        assert not check(validation_engine, contract, json.dumps(output), None)['accepted']


RULE_CONTROLS = [
    ({'id': 'r', 'kind': 'product_equals', 'operands': ['/a', '/b'], 'target': '/v'},
     [{'a': 0, 'b': 9, 'v': 0}, {'a': -2, 'b': 3, 'v': -6}],
     {'a': 2, 'b': 3, 'v': 7}, {'a': True, 'b': 3, 'v': 3}),
    ({'id': 'r', 'kind': 'sum_equals', 'operands': ['/a', '/b'], 'target': '/v'},
     [{'a': 0, 'b': 0, 'v': 0}, {'a': -2, 'b': 3, 'v': 1}],
     {'a': 2, 'b': 3, 'v': 4}, {'a': 1.5, 'b': 3, 'v': 4}),
    ({'id': 'r', 'kind': 'date_before', 'left': '/a', 'right': '/b'},
     [{'a': '2024-02-29', 'b': '2024-03-01'}, {'a': '2000-02-28', 'b': '2000-02-29'}],
     {'a': '2024-02-29', 'b': '2024-02-29'}, {'a': '1900-02-29', 'b': '1900-03-01'}),
    ({'id': 'r', 'kind': 'equals', 'left': '/a', 'right': '/b'},
     [{'a': {'x': 1, 'y': None}, 'b': {'y': None, 'x': 1.0}}, {'a': [False, 0], 'b': [False, 0.0]}],
     {'a': [1, 2], 'b': [2, 1]}, {'a': True, 'b': 1}),
    ({'id': 'r', 'kind': 'reference_member', 'target': '/v', 'contextLocation': '/choices'},
     [{'v': 1.0}, {'v': 2}], {'v': 3}, {'v': True}),
    ({'id': 'r', 'kind': 'member_of', 'target': '/v', 'arrayLocation': '/items'},
     [{'v': 1.0, 'items': [1, 2]}, {'v': 2, 'items': [1, 2]}],
     {'v': 3, 'items': [1, 2]}, {'v': 1, 'items': {}}),
    ({'id': 'r', 'kind': 'count_equals', 'target': '/v', 'arrayLocation': '/items'},
     [{'v': 0.0, 'items': []}, {'v': 2, 'items': [{}, {}]}],
     {'v': 1, 'items': []}, {'v': False, 'items': []}),
    ({'id': 'r', 'kind': 'sum_items_equals', 'target': '/v', 'arrayLocation': '/items', 'itemLocation': '/n'},
     [{'v': 0, 'items': []}, {'v': 10**80 - 1, 'items': [{'n': 10**80}, {'n': -1}]}],
     {'v': 2, 'items': [{'n': 1}]}, {'v': 1, 'items': [{'n': True}]}),
    ({'id': 'r', 'kind': 'division_equals', 'operands': ['/a', '/b'], 'target': '/v'},
     [{'a': 10, 'b': 2, 'v': 5.0}, {'a': 7.5, 'b': 2.5, 'v': 3.0}],
     {'a': 10, 'b': 2, 'v': 4.0}, {'a': True, 'b': 2, 'v': 5.0}),
    ({'id': 'r', 'kind': 'percentage_of', 'operands': ['/rate', '/total'], 'target': '/v'},
     [{'rate': 20, 'total': 100, 'v': 20.0}, {'rate': 50, 'total': 200, 'v': 100.0}],
     {'rate': 20, 'total': 100, 'v': 25.0}, {'rate': True, 'total': 100, 'v': 20.0}),
    ({'id': 'r', 'kind': 'unique_by', 'arrayLocation': '/items', 'itemLocation': '/id'},
     [{'items': []}, {'items': [{'id': True}, {'id': 1}, {'id': None}]}],
     {'items': [{'id': 1}, {'id': 1.0}]}, {'items': {}}),
]


def test_control_matrix_covers_every_registered_relationship_kind():
    assert {rule['kind'] for rule, *_ in RULE_CONTROLS} == KINDS


@pytest.mark.parametrize('rule,good,bad,wrong_type', RULE_CONTROLS, ids=lambda v: v['kind'] if isinstance(v, dict) and 'kind' in v else None)
def test_all_relationship_kinds_have_valid_alternatives_bad_and_missing_controls(validation_engine, rule, good, bad, wrong_type):
    contract = Contract('rule-control', '1', {'type': 'object', 'properties': {'owner': {'type': 'string'}}},
        bindings=[{'instanceLocation': '/owner', 'contextLocation': '/owner'}], relationships=[rule])
    context = approved({'owner': 'control', 'choices': [1, 2]}, ['/owner', '/choices'])
    for doc, valid, status in [(doc, True, 'valid') for doc in good] + [
            (bad, False, 'invalid'), (wrong_type, False, 'invalid'), ({}, False, 'needs_context')]:
        result = check(validation_engine, contract, {'owner': 'control', **doc}, context)
        assert result['accepted'] is valid and result['success'] is valid
        assert result['stages']['originalSchema'] == 'valid' and result['stages']['context'] == 'valid'
        assert result['stages']['relationships'] == status
        if not valid:
            assert result['errors'][0]['ruleId'] == 'r'
            assert result['errors'][0]['kind'] == rule['kind']


@pytest.mark.parametrize('state', ['absent', 'unapproved', 'partial', 'missing_value'])
def test_missing_required_context_never_turns_structure_only_into_approval(validation_engine, state):
    contract = Contract('missing-control', '1', {'type': 'object'}, bindings=[
        {'instanceLocation': '/owner', 'contextLocation': '/owner'},
        {'instanceLocation': '/other', 'contextLocation': '/other'}])
    context = (None if state == 'absent' else approved({'owner': 'control', 'other': 2}, []) if state == 'unapproved'
               else approved({'owner': 'control', 'other': 2}, ['/owner']) if state == 'partial'
               else approved({'owner': 'control'}, ['/owner', '/other']))
    result = check(validation_engine, contract, {'owner': 'control', 'other': 2}, context)
    assert result['result'] == 'NEEDS_CONTEXT' and not result['accepted']
    assert result['stages']['relationships'] == 'not_evaluated'
    assert result['context']['missingBindings']


@pytest.mark.parametrize('change', ['unconfirmed', 'expired', 'wrong_contract', 'expired_fact', 'unverified_fact'])
def test_bad_context_is_an_error_not_a_model_output_rejection(validation_engine, change):
    contract = Contract('context-control', '1', {'type': 'object'}, bindings=[
        {'instanceLocation': '/owner', 'contextLocation': '/owner'}])
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    context = approved()
    if change == 'unconfirmed':
        context['confirmed'] = False
    elif change == 'expired':
        context['expiresAt'] = past
    elif change == 'wrong_contract':
        context['contractHash'] = 'different-contract'
    else:
        context['facts'] = [{'contextLocation': '/owner', 'source': 'control', 'version': '1',
                             'verified': change != 'unverified_fact',
                             'expiresAt': past if change == 'expired_fact' else future}]
    with pytest.raises(ContextError):
        check(validation_engine, contract, {'owner': 'control'}, context)


@pytest.mark.parametrize('value,valid', [
    ({'a': 1, 'b': [False, None]}, True), ({'b': [False, None], 'a': 1.0}, True),
    ({'a': True, 'b': [False, None]}, False), ({'a': 1, 'b': [0, None]}, False),
    ({'a': 1, 'b': [None, False]}, False), ({'a': 1}, False),
])
def test_nested_const_uses_json_equality_not_python_truthiness_or_array_sets(validation_engine, value, valid):
    contract = Contract('const-control', '1', {'type': 'object'},
        bindings=[{'instanceLocation': '/payload', 'contextLocation': '/payload'}])
    context = approved({'payload': {'a': 1, 'b': [False, None]}}, ['/payload'])
    result = check(validation_engine, contract, {'payload': value}, context)
    assert result['accepted'] is valid


@pytest.mark.parametrize('value,valid', [('é', True), ('e\u0301', False)])
def test_bound_strings_remain_codepoint_exact(validation_engine, value, valid):
    contract = Contract('string-control', '1', {'type': 'object'},
        bindings=[{'instanceLocation': '/text', 'contextLocation': '/text'}])
    assert check(validation_engine, contract, {'text': value}, approved({'text': 'é'}, ['/text']))['accepted'] is valid


def test_missing_optional_binding_does_not_falsely_reject_or_claim_context_agreement(validation_engine):
    contract = Contract('optional-control', '1', {'type': 'object'},
        bindings=[{'instanceLocation': '/x', 'contextLocation': '/x', 'required': False}])
    result = check(validation_engine, contract, {'x': 'free value'}, None)
    assert result['accepted'] and not result['success'] and result['result'] == 'NOT_CHECKED'
    assert not result['context']['activeBindings'] and result['semanticValid'] is None


@pytest.mark.parametrize('state,status', [('approved', 'valid'), ('unapproved', 'needs_context'),
                                        ('absent', 'needs_context'), ('wrong_type', 'invalid')])
def test_reference_membership_requires_the_specific_approved_array(validation_engine, state, status):
    contract = Contract('reference-control', '1', {'type': 'object'},
        relationships=[{'id': 'member', 'kind': 'reference_member', 'target': '/choice', 'contextLocation': '/choices'}])
    data = {} if state == 'absent' else {'choices': {} if state == 'wrong_type' else [1, 2]}
    context = approved(data, [] if state in {'absent', 'unapproved'} else ['/choices'])
    result = check(validation_engine, contract, {'choice': 1}, context)
    assert result['stages']['relationships'] == status
    assert result['accepted'] is (state == 'approved')


@pytest.mark.parametrize('token', ['01', '-1', '+0', '-', '1.0', '١', '1025'])
def test_projection_rejects_noncanonical_and_out_of_range_array_indices(validation_engine, token):
    contract = Contract('array-control', '1', {'type': 'array', 'items': {'type': 'integer'}},
                        bindings=[{'instanceLocation': '/' + token, 'contextLocation': '/value'}])
    with pytest.raises(ContextError, match='Array binding'):
        check(validation_engine, contract, [0, 7], approved({'value': 7}, ['/value']))


@pytest.mark.parametrize('index', [0, 1024])
def test_projection_inclusive_index_limits(validation_engine, index):
    contract = Contract('array-limit', '1', {'type': 'array', 'items': {'type': 'integer'}},
                        bindings=[{'instanceLocation': '/' + str(index), 'contextLocation': '/value'}])
    output = [0] * index + [7]
    context = approved({'value': 7}, ['/value'])
    assert check(validation_engine, contract, output, context)['success']
    assert not check(validation_engine, contract, output[:-1], context)['accepted']


@pytest.mark.parametrize('name', ['01', '-', '١'])
def test_numeric_looking_object_keys_remain_legal_property_names(validation_engine, name):
    contract = Contract('object-pointer-control', '1', {'type': 'object'},
                        bindings=[{'instanceLocation': '/' + name, 'contextLocation': '/value'}])
    assert check(validation_engine, contract, {name: 7}, approved({'value': 7}, ['/value']))['success']


@pytest.mark.parametrize('raw', ['{"x":1,"x":2}', '{"x":NaN}', '{"x":1e999}', '{"x":1e-9999}',
                               '{}{}', '{} trailing', '```json\n{}\n```', '{"x":'])
def test_incorrect_raw_json_is_not_repaired_by_validation(validation_engine, raw):
    result = check(validation_engine, Contract('json-control', '1', True), raw, None)
    assert not result['accepted'] and result['stages']['json'] == 'invalid'
    assert result['stages']['originalSchema'] == 'not_evaluated'


@pytest.mark.parametrize('compute', [False, True])
@pytest.mark.parametrize('items,count,total', [([], 0, 0), ([{'n': -2}, {'n': 2}], 2, 0), ([{'n': 7}], 1, 7)])
def test_model_and_application_modes_share_valid_sets_and_source_gates(validation_engine, compute, items, count, total):
    schema = {'type': 'object', 'properties': {'items': {'type': 'array', 'items': {
        'type': 'object', 'properties': {'n': {'type': 'integer'}}, 'required': ['n']}},
        'count': {'type': 'integer'}, 'total': {'type': 'integer'}},
        'required': ['items', 'count', 'total'], 'additionalProperties': False}
    rules = [{'id': 'count', 'kind': 'count_equals', 'target': '/count', 'arrayLocation': '/items'},
             {'id': 'total', 'kind': 'sum_items_equals', 'target': '/total', 'arrayLocation': '/items', 'itemLocation': '/n'}]
    if compute:
        rules = [{**rule, 'compute': 'application'} for rule in rules]
    contract = Contract('calculation-control', '1', schema,
        bindings=[{'instanceLocation': '/items', 'contextLocation': '/items'}], relationships=rules)
    context = approved({'items': items}, ['/items'])
    output = {'items': copy.deepcopy(items)} if compute else {'items': copy.deepcopy(items), 'count': count, 'total': total}
    before = copy.deepcopy(output)
    result = validate_with_calculations(output, validation_engine, contract, context)
    assert result['accepted'] and result['parsed'] == {'items': items, 'count': count, 'total': total}
    assert output == before and not result['executionAuthorized']
    corrupt = {**output, 'items': [{'n': 999}]}
    assert not validate_with_calculations(corrupt, validation_engine, contract, context)['accepted']


@pytest.mark.parametrize('action', ['refuse', 'ask_clarification'])
def test_control_outcomes_are_not_successful_data_answers(validation_engine, action):
    contract = Contract('tool-control', '1', {'type': 'object'}, 'tool_envelope', 'save',
                        bindings=[{'instanceLocation': '/owner', 'contextLocation': '/owner'}])
    output = envelope(action, missing=['owner'] if action == 'ask_clarification' else [], reason='Need approved data.')
    result = check(validation_engine, contract, output, None)
    assert result['accepted'] and not result['success'] and result['semanticValid'] is None
    assert result['result'] == ('REFUSED' if action == 'refuse' else 'NEEDS_CONTEXT')
    assert not check(validation_engine, contract, {**output, 'tool': 'save'}, None)['accepted']


def test_known_truncation_is_not_accepted_even_if_json_and_rules_pass(validation_engine):
    contract, context, ids = station_choice()
    result = validate_contract({'stationId': ids[0], 'travellers': 1}, validation_engine, contract, context,
        generation=Generation('{}', metadata={'finish_reason': 'length'}))
    assert not result['accepted'] and result['errors'][-1]['code'] == 'OUTPUT_TRUNCATED'


@pytest.mark.parametrize('value', [None, False, 0, '', [], {}])
def test_root_bindings_support_all_json_value_types_without_confusing_empty_with_absent(validation_engine, value):
    contract = Contract('root-control', '1', True,
                        bindings=[{'instanceLocation': '', 'contextLocation': '/value'}])
    result = check(validation_engine, contract, json.dumps(value), approved({'value': value}, ['/value']))
    assert result['accepted'] and result['success']
    absent = check(validation_engine, contract, None, approved({'value': value}, ['/value']))
    assert not absent['accepted'] and absent['stages']['json'] == 'not_evaluated'
