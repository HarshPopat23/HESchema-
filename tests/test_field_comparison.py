import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from heschema.contracts import Contract
from heschema.field_comparison import FIELD_COMPARISON_DIALECT, META_SCHEMA
from heschema.providers import Provider, ProviderError
from heschema.schema import SchemaEngine, check_schema
from heschema.validation import validate_contract

CASES = json.loads(
    (Path(__file__).resolve().parents[1] / 'vocabulary/field-comparison/v1/cases.json').read_text()
)
RULE = {'left': '/min', 'right': '/max', 'operator': 'lte', 'mode': 'number'}
DIALECT = {'$schema': FIELD_COMPARISON_DIALECT}


@pytest.mark.parametrize(('schema', 'case'), [
    pytest.param(group['schema'], case, id=case['description'])
    for group in CASES for case in group['tests']
])
def test_conformance(schema, case):
    errors = SchemaEngine().errors({**DIALECT, **schema}, case['data'])
    assert (not errors) == case['valid']
    if errors:
        assert errors[0]['keyword'] == 'compareFields'


@pytest.mark.parametrize('rules', [[], [{}], [{**RULE, 'left': '/bad~2'}],
                                   [{**RULE, 'mode': 'json'}], [{**RULE, 'extra': 1}]])
def test_invalid_keyword_in_nested_schema(rules):
    Draft202012Validator.check_schema(META_SCHEMA)
    with pytest.raises(ValueError, match='Invalid JSON Schema'):
        check_schema({**DIALECT, '$defs': {'inner': {'compareFields': rules}}})


def test_dialect_boundaries():
    with pytest.raises(ValueError, match='requires the HESchema'):
        check_schema({'compareFields': [RULE]})
    with pytest.raises(ValueError, match='root without nested'):
        check_schema({**DIALECT, 'items': {**DIALECT, 'compareFields': [RULE]}})
    with pytest.raises(ValueError, match='schema nodes'):
        check_schema({**DIALECT, 'default': {'compareFields': [RULE]}, '$ref': '#/default'})
    with pytest.raises(ValueError, match='Blaze does not support'):
        SchemaEngine(backend='blaze').register({**DIALECT, 'compareFields': [RULE]})
    check_schema({'const': {'compareFields': 17}})


def test_local_reference_and_diagnostic_locations():
    schema = {
        **DIALECT,
        '$defs': {'limits': {'compareFields': [RULE]}},
        'properties': {'limits': {'$ref': '#/$defs/limits'}},
    }
    engine = SchemaEngine()
    assert engine.errors(schema, {'limits': {'min': 1, 'max': 3}}) == []
    error, = engine.errors(schema, {'limits': {'min': 4, 'max': 3}})
    assert error['instanceLocation'] == '/limits'
    assert error['schemaLocation'] == '/$defs/limits/compareFields'


@pytest.mark.parametrize('kind', ['document', 'tool_envelope'])
def test_contract_runtime(kind):
    schema = {
        **DIALECT,
        'type': 'object',
        '$defs': {'limits': {'compareFields': [RULE]}},
        '$ref': '#/$defs/limits',
    }
    contract = Contract(id='limits', version='1', schema=schema, outputKind=kind,
                        tool='configure' if kind == 'tool_envelope' else None)

    def output(values):
        if kind == 'document':
            return values
        return {'action': 'call_tool', 'tool': 'configure', 'arguments': values,
                'missingFields': [], 'reason': ''}

    engine = SchemaEngine()
    assert validate_contract(output({'min': 1, 'max': 3}), engine, contract)['accepted']
    assert not validate_contract(output({'min': 4, 'max': 3}), engine, contract)['accepted']
    assert schema['$schema'] == FIELD_COMPARISON_DIALECT


@pytest.mark.asyncio
async def test_native_provider_rejects_custom_dialect():
    provider = Provider('mock', 'mock')
    try:
        with pytest.raises(ProviderError, match='use prompt_only'):
            await provider.generate([], format_schema={**DIALECT, 'compareFields': [RULE]})
    finally:
        await provider.close()


def test_multiple_comparisons_and_array_indices():
    rules = [
        {**RULE, 'left': '/points/0', 'right': '/points/1', 'operator': 'lt'},
        {**RULE, 'left': '/points/1', 'right': '/points/0', 'operator': 'gte'},
        {**RULE, 'left': '/points/1', 'right': '/points/0', 'operator': 'gt'},
        {**RULE, 'left': '/a', 'right': '/b', 'operator': 'ne', 'mode': 'json'},
    ]
    engine = SchemaEngine()
    schema = {**DIALECT, 'compareFields': rules}
    assert engine.errors(schema, {'points': [1, 2], 'a': 1, 'b': True}) == []
    error, = engine.errors(schema, {'points': [1, 2], 'a': 1, 'b': 1.0})
    assert 'Comparison 3 failed' in error['message']
    error, = engine.errors({**DIALECT, 'compareFields': [{**rules[0], 'left': '/points/00'}]},
                           {'points': [1, 2]})
    assert 'could not resolve operand' in error['message']
