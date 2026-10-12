import pytest

from heschema.contracts import Contract
from heschema.diagnostics import parts, pointer
from heschema.rules import evaluate_rules
from heschema.schema import SchemaEngine
from heschema.validation import validate_contract

INVOICE = Contract('invoice', '1', {'type': 'object', 'properties': {k: {'type': 'integer'} for k in ['quantity', 'unitPriceMinor', 'totalMinor']}, 'required': ['quantity', 'unitPriceMinor', 'totalMinor'], 'additionalProperties': False},
                   bindings=[{'instanceLocation': '/' + k, 'contextLocation': '/' + k} for k in ['quantity', 'unitPriceMinor']],
                   relationships=[{'id': 'total', 'kind': 'product_equals', 'operands': ['/quantity', '/unitPriceMinor'], 'target': '/totalMinor'}])
CTX = {'id': 'invoice-source', 'version': 1, 'confirmed': True, 'data': {'quantity': 2, 'unitPriceMinor': 1250}, 'approvedPointers': ['/quantity', '/unitPriceMinor'], 'facts': []}


def test_invoice_structure_source_and_exact_product_are_independent():
    engine = SchemaEngine()
    bad = validate_contract({'quantity': 2, 'unitPriceMinor': 1250, 'totalMinor': 25}, engine, INVOICE, CTX)
    assert bad['referenceSchemaValid'] and bad['stages']['relationships'] == 'invalid'
    assert bad['errors'][0]['expected'] == 2500
    good = validate_contract({'quantity': 2, 'unitPriceMinor': 1250, 'totalMinor': 2500}, engine, INVOICE, CTX)
    assert good['success'] and not good['executionAuthorized']
    wrong_source = validate_contract({'quantity': 3, 'unitPriceMinor': 1250, 'totalMinor': 3750}, engine, INVOICE, CTX)
    assert wrong_source['stages']['context'] == 'invalid'
    assert wrong_source['stages']['relationships'] == 'not_evaluated'
    missing = validate_contract({'quantity': 2, 'unitPriceMinor': 1250, 'totalMinor': 2500}, engine, INVOICE)
    assert missing['result'] == 'NEEDS_CONTEXT' and missing['semanticValid'] is None


def test_exact_arithmetic_large_values_booleans_and_sum():
    rule = INVOICE.relationships
    huge = 10**100
    assert evaluate_rules({'quantity': huge, 'unitPriceMinor': 7, 'totalMinor': huge * 7}, rule)['status'] == 'valid'
    assert evaluate_rules({'quantity': True, 'unitPriceMinor': 7, 'totalMinor': 7}, rule)['status'] == 'invalid'
    summation = [{'id': 'sum', 'kind': 'sum_equals', 'operands': ['/a', '/b'], 'target': '/sum'}]
    assert evaluate_rules({'a': 10, 'b': 20, 'sum': 30}, summation)['status'] == 'valid'
    assert evaluate_rules({'a': 10, 'b': 20.0, 'sum': 30}, summation)['status'] == 'valid'
    assert evaluate_rules({'a': 10, 'b': 20.5, 'sum': 30}, summation)['status'] == 'invalid'
    assert evaluate_rules({'a': 10, 'b': 1e25, 'sum': 1e25}, summation)['status'] == 'invalid'


@pytest.mark.parametrize('first,second,status', [('2026-01-01', '2026-01-02', 'valid'), ('2026-01-02', '2026-01-01', 'invalid'), ('2026-01-01', '2026-01-01', 'invalid'), ('2026-02-30', '2026-03-01', 'invalid'), ('20260101', '2026-01-02', 'invalid')])
def test_date_order_is_parsed_strictly(first, second, status):
    r = [{'id': 'dates', 'kind': 'date_before', 'left': '/start', 'right': '/end'}]
    assert evaluate_rules({'start': first, 'end': second}, r)['status'] == status


def test_missing_reference_unapproved_evidence_and_pointer_locations():
    r = [{'id': 'member', 'kind': 'reference_member', 'target': '/id', 'contextLocation': '/ids'}]
    assert evaluate_rules({'id': 1}, r)['status'] == 'needs_context'
    assert evaluate_rules({'id': True}, r, {'ids': [1]})['status'] == 'invalid'
    assert evaluate_rules({'id': 1}, r, {'ids': [1]}, set())['status'] == 'needs_context'
    assert pointer(['a/b~c', 0]) == '/a~1b~0c/0'
    assert parts('/a~1b~0c/0') == ['a/b~c', '0']
    assert pointer([]) == ''
    engine = SchemaEngine()
    error = engine.errors({'properties': {'a/b~c': {'type': 'integer'}}}, {'a/b~c': 'wrong'})[0]
    assert error['instanceLocation'] == '/a~1b~0c'
    assert engine.errors({'type': 'integer'}, 'wrong')[0]['instanceLocation'] == ''
    disjunction = engine.errors({'oneOf': [{'type': 'integer'}, {'type': 'boolean'}]}, 'wrong')[0]
    assert len(disjunction['details']) == 2 and 'schemaLocation' in disjunction['details'][0]


def test_reference_errors_identify_original_definition_and_preserve_evaluation_path():
    schema = {'$defs': {'n': {'type': 'integer'}}, 'properties': {'x': {'$ref': '#/$defs/n'}}}
    engine = SchemaEngine()
    error = engine.errors(schema, {'x': 'wrong'})[0]
    assert error['schemaLocation'] == '/$defs/n/type'
    assert error['evaluationLocation'] == '/properties/x/type'
    assert engine.timing_snapshot()['pythonReferenceMs'] >= 0
