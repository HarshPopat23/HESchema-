"""Constructed negative controls, including unchanged public-source study records.

These tests verify routing and safety, not live-model recovery improvements.
"""

import asyncio
import copy
from pathlib import Path

import pytest
from test_relationships import CTX, INVOICE

from heschema.calculations import validate_with_calculations
from heschema.contracts import Contract
from heschema.diagnostics import runtime_feedback
from heschema.jsonio import canonical, loads
from heschema.providers import Generation
from heschema.repair import RepairLimits, coordinate, feedback_message
from heschema.schema import SchemaEngine
from heschema.validation import envelope, validate_contract

ROOT = Path(__file__).resolve().parents[1]


def entries(errors, **kwargs):
    return loads(feedback_message(errors, **kwargs).split(': ', 1)[1])


@pytest.fixture
def engine():
    engine = SchemaEngine()
    yield engine
    engine.close()


@pytest.mark.parametrize('case_id,field,key', [
    ('CR-001', 'authors', 'given'), ('PYPI-001', 'files', 'filename'),
    ('WF-007', 'files', 'id'),
])
@pytest.mark.parametrize('application', [False, True])
def test_public_source_mismatch_identifies_one_leaf_without_echoing_whole_records(engine, case_id, field, key, application):
    cases = loads((ROOT / 'research/contract-main-study-v1/inputs/cases.json').read_text())
    case = next(case for case in cases if case['id'] == case_id)
    definition, document = copy.deepcopy(case['contract']), copy.deepcopy(case['expected_output'])
    if application:
        for rule in definition['relationships']:
            if rule['kind'] in {'count_equals', 'sum_items_equals'}:
                rule['compute'] = 'application'
                document.pop(rule['target'][1:])
    expected = document[field][0][key]
    document[field][0][key] = 'constructed-negative-control'
    before = copy.deepcopy(document)
    validate = validate_with_calculations if application else validate_contract
    result = validate(canonical(document), engine, Contract(**definition), case['context'])
    errors_before = copy.deepcopy(result['errors'])
    feedback = entries(result['errors'])
    assert feedback[0]['category'] == 'source_value'
    source = feedback[0]['sourceMismatch']
    assert source['instanceLocation'] == f'/{field}/0/{key}'
    assert source['contextLocation'].endswith(f'/0/{key}')
    assert source['actual'] == 'constructed-negative-control' and source['expected'] == expected
    assert len(feedback_message(result['errors'])) < 1200
    assert document == before and result['errors'] == errors_before
    assert not result['accepted']
    if application:
        assert result['calculation']['status'] == 'blocked' and not result['calculation']['values']


def bound_contract(value, *, keyword='const', output_kind='document'):
    contract = Contract('bound', '1', {'type': 'object', 'properties': {'a/b~c': {}}},
                        outputKind=output_kind, tool='save' if output_kind == 'tool_envelope' else None,
                        bindings=[{'instanceLocation': '/a~1b~0c', 'contextLocation': '/facts', 'keyword': keyword}])
    context = {'id': 'approved', 'version': 1, 'confirmed': True, 'data': {'facts': value},
               'approvedPointers': ['/facts'], 'facts': []}
    return contract, context


@pytest.mark.parametrize('actual,expected,suffix,marker', [
    ({}, {'nested': None}, '/nested', 'actualMissing'),
    ({'nested': None}, {}, '/nested', 'expectedMissing'),
    ([], [None], '/0', 'actualMissing'),
    ([None], [], '/0', 'expectedMissing'),
    ({'x/y~z': False}, {'x/y~z': 0}, '/x~1y~0z', None),
    ([2, 1], [1, 2], '/0', None),
])
@pytest.mark.parametrize('kind', ['document', 'tool_envelope'])
def test_source_paths_escaping_absence_null_and_order(engine, actual, expected, suffix, marker, kind):
    contract, context = bound_contract(expected, output_kind=kind)
    doc = {'a/b~c': actual}
    raw = envelope('call_tool', 'save', doc) if kind == 'tool_envelope' else doc
    result = validate_contract(raw, engine, contract, context)
    mismatch = entries(result['errors'])[0]['sourceMismatch']
    assert mismatch['instanceLocation'] == '/a~1b~0c' + suffix
    assert mismatch['contextLocation'] == '/facts' + suffix
    if marker:
        assert mismatch[marker] is True
        assert ('actual' if marker == 'actualMissing' else 'expected') not in mismatch
    assert not result['accepted']


@pytest.mark.parametrize('keyword,approved,actual', [('enum', [2, 4], 3), ('minimum', 2, 1), ('maximum', 4, 5)])
def test_source_limits_are_constraints_not_instructions_to_copy_a_replacement(engine, keyword, approved, actual):
    contract, context = bound_contract(approved, keyword=keyword)
    result = validate_contract({'a/b~c': actual}, engine, contract, context)
    mismatch = entries(result['errors'])[0]['sourceMismatch']
    assert mismatch['keyword'] == keyword and mismatch['constraint'] == approved
    assert 'expected' not in mismatch


def test_missing_bound_field_and_unapproved_context_are_distinct(engine):
    contract, context = bound_contract(None)
    error = validate_contract({}, engine, contract, context)['errors'][0]
    mismatch = entries([error])[0]['sourceMismatch']
    assert mismatch['actualMissing'] and mismatch['expected'] is None
    unapproved = {**context, 'approvedPointers': []}
    result = validate_contract({'a/b~c': 'wrong'}, engine, contract, unapproved)
    assert runtime_feedback(result['errors'], allow_state=True) == []
    assert all('sourceMismatch' not in error for error in result['errors'])


def test_large_first_error_does_not_hide_later_diagnostics_or_emit_broken_json(engine):
    # A labelled size-stress control, not a claimed production/model response.
    value = ['source-field-' + str(i) for i in range(800)]
    contract, context = bound_contract(value)
    first = validate_contract({'a/b~c': ['wrong', *value[1:]]}, engine, contract, context)['errors'][0]
    assert len(first['message']) > 4000
    second = {'code': 'JSON_INVALID', 'message': 'Expecting property name'}
    feedback = entries([first, second])
    assert [entry['category'] for entry in feedback] == ['source_value', 'invalid_json']
    assert feedback[0]['sourceMismatch']['expected'] == value[0]
    for budget in (128, 180, 256, 512, 1000, 4000):
        message = feedback_message([first, second], max_chars=budget)
        assert len(message) <= budget
        assert loads(message.split(': ', 1)[1])  # A whole, nonempty JSON list.


def test_long_diagnostic_cannot_starve_a_short_later_error():
    errors = [{'code': 'SCHEMA_INVALID', 'message': 'x' * 20000, 'instanceLocation': '/' + 'x' * 20000},
              {'code': 'JSON_INVALID', 'message': 'Extra data'}]
    result = entries(errors, max_chars=512)
    assert [e['category'] for e in result] == ['schema', 'invalid_json']


@pytest.mark.parametrize('text', ['{"x":1}}', '{"x":', '{"x":1,"x":2}', '{"x":NaN}'])
def test_json_diagnostics_preserve_parser_evidence_without_inventing_offsets(engine, text):
    result = validate_contract(text, engine, Contract('json', '1', {}))
    error = result['errors'][0]
    feedback = entries([error])[0]
    assert feedback['category'] == 'invalid_json'
    assert feedback.get('jsonError') == error.get('jsonError')
    if 'jsonError' not in error:
        assert 'jsonError' not in feedback
    assert 'preserve approved field values' in feedback['repairHint']
    assert not result['accepted'] and result['parsed'] is None


def test_schema_constraint_is_not_misclassified_as_a_wrong_source_value(engine):
    result = validate_contract({'quantity': 'two', 'unitPriceMinor': 1250, 'totalMinor': 2500}, engine, INVOICE, CTX)
    feedback = entries(result['errors'])[0]
    assert feedback['category'] == 'schema' and feedback['keyword'] == 'type'
    assert feedback['instanceLocation'] == '/quantity'
    assert result['stages']['relationships'] == 'not_evaluated'
    branch_error = engine.errors({'oneOf': [{'type': 'integer'}, {'type': 'boolean'}]}, 'bad')[0]
    assert len(entries([branch_error])[0]['branches']) == 2


def test_arithmetic_feedback_retains_inputs_target_result_and_protected_fields(engine):
    result = validate_contract({'quantity': 2, 'unitPriceMinor': 1250, 'totalMinor': 25}, engine, INVOICE, CTX)
    feedback = entries(result['errors'])[0]
    assert feedback['category'] == 'relationship' and feedback['ruleId'] == 'total'
    assert feedback['actual'] == 25 and feedback['expected'] == 2500
    assert feedback['inputLocations'] == ['/totalMinor', '/quantity', '/unitPriceMinor']
    assert feedback['protectedInputs'] == ['/quantity', '/unitPriceMinor']
    assert 'product' in feedback['repairHint'] and 'Preserve all approved inputs' in feedback['repairHint']


def test_date_order_does_not_instruct_copying_the_right_date(engine):
    contract = Contract('date', '1', {'type': 'object'}, relationships=[
        {'id': 'order', 'kind': 'date_before', 'left': '/start', 'right': '/end'}])
    result = validate_contract({'start': '2026-02-01', 'end': '2026-01-01'}, engine, contract)
    assert 'strictly before' in entries(result['errors'])[0]['repairHint']


def test_relationship_type_failure_receives_one_bounded_repair(engine):
    contract = Contract('date', '1', {'type': 'object'}, relationships=[
        {'id': 'order', 'kind': 'date_before', 'left': '/start', 'right': '/end'}])
    seen = []
    async def generate(messages, attempt):
        seen.append(copy.deepcopy(messages))
        return Generation(canonical({'start': 'bad-date' if attempt == 0 else '2026-01-01', 'end': '2026-02-01'}))
    result = asyncio.run(coordinate(generate,
        lambda g: validate_contract(g.text, engine, contract, generation=g), [], limits=RepairLimits(1)))
    feedback = loads(seen[1][-1]['content'].split(': ', 1)[1])[0]
    assert feedback['code'] == 'RELATION_TYPE_INVALID' and feedback['category'] == 'relationship'
    assert feedback['inputLocations'] == ['/start', '/end']
    assert result['finalEvaluation']['accepted'] and result['requestsAttempted'] == 2
    assert result['feedbackVersion'] == 'category-v1'
    recorded = result['attempts'][0]['repairFeedback']
    assert recorded['message'] == seen[1][-1]['content'] and recorded['chars'] == len(recorded['message'])
    assert 'repairFeedback' not in result['attempts'][1]


def test_calculation_feedback_corrects_inputs_without_requesting_omitted_target(engine):
    contract = Contract('calc', '1', {'type': 'object', 'additionalProperties': False,
        'properties': {'items': {'type': 'array'}, 'count': {'type': 'integer'}},
        'required': ['items', 'count']}, relationships=[
            {'id': 'sum', 'kind': 'sum_items_equals', 'arrayLocation': '/items',
             'itemLocation': '/n', 'target': '/count', 'compute': 'application'}])
    result = validate_with_calculations({'items': [{'n': 'wrong'}]}, engine, contract)
    feedback = entries(result['errors'])[0]
    assert feedback['code'] == 'CALCULATION_INPUT_INVALID'
    assert feedback['inputLocations'] == ['/items']
    assert 'targets omitted' in feedback['repairHint']
    assert not result['accepted'] and result['calculation']['values'] == []


def test_hidden_oracle_errors_do_not_become_runtime_feedback():
    errors = [{'code': code, 'expected': 'hidden-gold'} for code in
              ('GROUND_TRUTH_MISMATCH', 'WRONG_ACTION', 'WRONG_TOOL', 'CONTEXT_REQUIRED', 'RELATION_INPUT_MISSING')]
    assert runtime_feedback(errors, allow_state=True) == []
    assert runtime_feedback([{'code': 'RELATION_TYPE_INVALID', 'repair': 'needs_context'}]) == []


def test_each_retry_is_revalidated_and_category_changes_with_the_actual_failure(engine):
    good = {'quantity': 2, 'unitPriceMinor': 1250, 'totalMinor': 2500}
    outputs = [canonical(good) + '}', canonical({**good, 'quantity': 3}),
               canonical({**good, 'totalMinor': 25}), canonical(good)]
    seen = []
    async def generate(messages, attempt):
        seen.append(copy.deepcopy(messages))
        return Generation(outputs[attempt])
    result = asyncio.run(coordinate(generate,
        lambda g: validate_contract(g.text, engine, INVOICE, CTX, generation=g), [], limits=RepairLimits(3)))
    categories = [loads(message[-1]['content'].split(': ', 1)[1])[0]['category'] for message in seen[1:]]
    assert categories == ['invalid_json', 'source_value', 'relationship']
    assert [a['generation']['text'] for a in result['attempts']] == outputs
    assert [a['evaluation']['accepted'] for a in result['attempts']] == [False, False, False, True]
    assert result['requestsAttempted'] == 4 and result['repairAttempts'] == 3
    assert result['finalEvaluation']['success'] and not result['finalEvaluation']['executionAuthorized']


def test_missing_evidence_does_not_become_a_relationship_type_repair(engine):
    contract = Contract('missing', '1', {'type': 'object'}, relationships=[
        {'id': 'member', 'kind': 'reference_member', 'target': '/id', 'contextLocation': '/ids'}])
    async def generate(messages, attempt):
        return Generation('{"id":1}')
    result = asyncio.run(coordinate(generate,
        lambda g: validate_contract(g.text, engine, contract, generation=g), [], limits=RepairLimits(5)))
    assert result['stopReason'] == 'needs_context' and result['requestsAttempted'] == 1
    assert 'repairFeedback' not in result['attempts'][0]


def test_raw_and_generic_comparators_keep_their_existing_rendering():
    error = {'code': 'SCHEMA_INVALID', 'message': 'bad type', 'instanceLocation': '/n'}
    assert entries([error], style='raw') == [error]
    assert feedback_message([error], 'generic') == (
        'The final output failed validation. Return corrected whole JSON using the same contract and approved context.')
