import json
from pathlib import Path

import pytest

from heschema.contracts import Contract
from heschema.field_comparison import FIELD_COMPARISON_DIALECT
from heschema.providers import Provider, ProviderError
from heschema.rules import evaluate_rules
from heschema.schema import SchemaEngine, check_schema
from heschema.unique_keys import RELATIONSHIPS_DIALECT
from heschema.validation import validate_contract

CASES = json.loads(
    (Path(__file__).resolve().parents[1] / 'vocabulary/keyed-uniqueness/v1/cases.json')
    .read_text(encoding='utf-8')
)
DIALECT = {'$schema': RELATIONSHIPS_DIALECT}


@pytest.mark.parametrize(('schema', 'case'), [
    pytest.param(group['schema'], case, id=case['description'])
    for group in CASES for case in group['tests']
])
def test_conformance(schema, case):
    errors = SchemaEngine().errors({**DIALECT, **schema}, case['data'])
    assert (not errors) == case['valid']
    if errors:
        assert errors[0]['keyword'] == 'uniqueKeys'


@pytest.mark.parametrize('value', [[], '/id', [5], ['/bad~2'], ['#/@id']])
def test_malformed_keyword_in_nested_schema(value):
    with pytest.raises(ValueError, match='Invalid JSON Schema'):
        check_schema({**DIALECT, '$defs': {'nested': {'uniqueKeys': value}}})


@pytest.mark.parametrize('dialect', [{}, {'$schema': FIELD_COMPARISON_DIALECT}])
def test_keyword_requires_its_vocabulary(dialect):
    with pytest.raises(ValueError, match='uniqueKeys requires'):
        check_schema({**dialect, 'uniqueKeys': ['/sku']})
    check_schema({**dialect, 'const': {'uniqueKeys': ['/sku']}})


def test_composed_dialect_and_referenced_diagnostic():
    schema = {
        **DIALECT,
        '$defs': {'records': {'uniqueKeys': ['/sku']}},
        'properties': {'records': {'$ref': '#/$defs/records'}},
        'compareFields': [{'left': '/min', 'right': '/max', 'mode': 'number', 'operator': 'lte'}],
    }
    engine = SchemaEngine()
    assert engine.errors(schema, {'records': [{'sku': 'A'}, {'sku': 'B'}], 'min': 1, 'max': 2}) == []
    errors = engine.errors(schema, {'records': [{'sku': 'A'}, {'sku': 'A'}], 'min': 3, 'max': 2})
    keyed, comparison = errors
    assert keyed['instanceLocation'] == '/records/1'
    assert keyed['schemaLocation'] == '/$defs/records/uniqueKeys'
    assert comparison['keyword'] == 'compareFields'
    schema['properties']['records']['compareFields'] = []
    with pytest.raises(ValueError, match='Invalid JSON Schema'):
        check_schema(schema)


def test_required_keys_and_legacy_missing_behavior():
    schema = {**DIALECT, 'uniqueKeys': ['/sku'],
              'items': {'type': 'object', 'required': ['sku']}}
    error, = SchemaEngine().errors(schema, [{}])
    assert error['keyword'] == 'required'
    rules = [{'id': 'sku', 'kind': 'unique_by', 'arrayLocation': '', 'itemLocation': '/sku'}]
    assert evaluate_rules([{}], rules)['status'] == 'needs_context'


@pytest.mark.parametrize('kind', ['document', 'tool_envelope'])
def test_contract_runtime(kind):
    schema = {**DIALECT, 'type': 'object',
              'properties': {'items': {'type': 'array', 'uniqueKeys': ['/sku']}}}
    contract = Contract(id='order', version='1', schema=schema, outputKind=kind,
                        tool='order' if kind == 'tool_envelope' else None)

    def output(last):
        doc = {'items': [{'sku': 'A'}, {'sku': last}]}
        return doc if kind == 'document' else {
            'action': 'call_tool', 'tool': 'order', 'arguments': doc,
            'missingFields': [], 'reason': '',
        }

    engine = SchemaEngine()
    assert validate_contract(output('B'), engine, contract)['accepted']
    assert not validate_contract(output('A'), engine, contract)['accepted']


@pytest.mark.asyncio
async def test_native_paths_reject_custom_dialect():
    schema = {**DIALECT, 'uniqueKeys': ['/sku']}
    with pytest.raises(ValueError, match='Blaze does not support'):
        SchemaEngine(backend='blaze').register(schema)
    provider = Provider('mock', 'mock')
    try:
        with pytest.raises(ProviderError, match='use prompt_only') as error:
            await provider.generate([], format_schema=schema)
        assert error.value.requests == 0
    finally:
        await provider.close()
