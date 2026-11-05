import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from heschema.contracts import Contract
from heschema.exact_arithmetic import DIALECT, META_SCHEMA
from heschema.ordering import DIALECT as V3_DIALECT
from heschema.providers import Provider, ProviderError
from heschema.schema import SchemaEngine, check_schema
from heschema.validation import validate_contract

CASES = json.loads(
    (Path(__file__).resolve().parents[1] / 'vocabulary/relationships/v4/cases.json')
    .read_text(encoding='utf-8')
)
V4 = {'$schema': DIALECT}
RULE = {'left': '/a', 'right': '/b', 'result': '/r', 'operation': 'multiply'}


@pytest.mark.parametrize(('schema', 'case'), [
    pytest.param(group['schema'], case, id=case['description'])
    for group in CASES for case in group['tests']
])
def test_conformance(schema, case):
    errors = SchemaEngine().errors({**V4, **schema}, case['data'])
    assert (not errors) == case['valid']
    if errors:
        assert errors[0]['keyword'] == 'arithmeticEquals'


@pytest.mark.parametrize('fragment', [
    {'arithmeticEquals': []},
    {'arithmeticEquals': [{**RULE, 'left': '/bad~2'}]},
    {'arithmeticEquals': [{**RULE, 'operation': 'sqrt'}]},
    {'arithmeticEquals': [{**RULE, 'rounding': {'mode': 'half-even'}}]},
    {'arithmeticEquals': [{**RULE, 'rounding': {'mode': 'half-even', 'scale': 19}}]},
    {'arithmeticEquals': [{**RULE, 'rounding': {'mode': 'half-even', 'scale': True}}]},
    {'arithmeticEquals': [{**RULE, 'rounding': {'mode': 'automatic', 'scale': 2}}]},
    {'arithmeticEquals': [{**RULE, 'tolerance': '0.01'}]},
    {'sortedBy': []},
    {'localReferences': [
        {'source': {'array': '/left', 'keys': ['']}, 'target': {'array': '/right', 'keys': ['/a', '/b']}},
    ]},
])
def test_rejects_invalid_nested_schema(fragment):
    Draft202012Validator.check_schema(META_SCHEMA)
    with pytest.raises(ValueError, match='Invalid JSON Schema'):
        check_schema({**V4, '$defs': {'invoice': fragment}, '$ref': '#/$defs/invoice'})


@pytest.mark.parametrize('dialect', [{}, {'$schema': V3_DIALECT}])
def test_keyword_requires_v4_opt_in(dialect):
    with pytest.raises(ValueError, match='arithmeticEquals requires'):
        check_schema({**dialect, 'arithmeticEquals': [RULE]})
    check_schema({**dialect, 'const': {'arithmeticEquals': [RULE]}})


def test_missing_operands_and_referenced_diagnostics():
    rule = {**RULE, 'left': '/a~1b', 'operation': 'divide'}
    schema = {
        **V4, '$defs': {'line': {'arithmeticEquals': [rule]}},
        'properties': {'line': {'$ref': '#/$defs/line'}},
    }
    engine = SchemaEngine()
    error, = engine.errors(schema, {'line': {'b': '1', 'r': '2'}})
    assert error['instanceLocation'] == '/line/a~1b'
    assert error['schemaLocation'] == '/$defs/line/arithmeticEquals'
    error, = engine.errors(schema, {'line': {'a/b': '2', 'b': '0', 'r': '2'}})
    assert error['instanceLocation'] == '/line/b'
    assert 'Division by zero' in error['message']
    error, = engine.errors(schema, {'line': {'a/b': '2', 'b': '1'}})
    assert error['instanceLocation'] == '/line/r'


def test_rounding_carry_overflow_and_inherited_keyword():
    schema = {
        **V4, 'arithmeticEquals': [
            {**RULE, 'operation': 'add', 'rounding': {'scale': 0.0, 'mode': 'half-up'}},
        ],
        'properties': {'items': {'uniqueKeys': ['']}},
    }
    engine = SchemaEngine()
    assert not engine.errors(schema, {'a': '0.5', 'b': '1', 'r': '2', 'items': [1, 2]})
    error, = engine.errors(schema, {'a': '0.5', 'b': '1', 'r': '2', 'items': [1, 1.0]})
    assert error['keyword'] == 'uniqueKeys'
    error, = engine.errors(schema, {'a': '9' * 38, 'b': '0.5', 'r': '0'})
    assert 'outside the decimal' in error['message']


@pytest.mark.parametrize('kind', ['document', 'tool_envelope'])
def test_contract_runtime(kind):
    schema = {**V4, 'type': 'object', 'arithmeticEquals': [RULE]}
    contract = Contract(id='invoice', version='1', schema=schema, outputKind=kind,
                        tool='invoice' if kind == 'tool_envelope' else None)

    def output(total):
        doc = {'a': '2', 'b': '12.50', 'r': total}
        return doc if kind == 'document' else {
            'action': 'call_tool', 'tool': 'invoice', 'arguments': doc,
            'missingFields': [], 'reason': '',
        }

    engine = SchemaEngine()
    assert validate_contract(output('25.00'), engine, contract)['accepted']
    assert not validate_contract(output('24.99'), engine, contract)['accepted']


@pytest.mark.asyncio
async def test_native_routes_reject_custom_dialect():
    schema = {**V4, 'arithmeticEquals': [RULE]}
    with pytest.raises(ValueError, match='Blaze does not support'):
        SchemaEngine(backend='blaze').register(schema)
    provider = Provider('mock', 'mock')
    try:
        with pytest.raises(ProviderError, match='use prompt_only') as error:
            await provider.generate([], format_schema=schema)
        assert error.value.requests == 0
    finally:
        await provider.close()
