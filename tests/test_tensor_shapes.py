import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from heschema.contracts import Contract
from heschema.ordering import DIALECT as RELATIONSHIPS_DIALECT
from heschema.providers import Provider, ProviderError
from heschema.schema import SchemaEngine, check_schema
from heschema.tensor_shapes import DIALECT, META_SCHEMA
from heschema.validation import validate_contract

CASES = json.loads(
    (Path(__file__).resolve().parents[1] / 'vocabulary/ml/v1/cases.json').read_text(encoding='utf-8')
)
ML = {'$schema': DIALECT}
TENSORS = [{'path': '/x', 'shape': ['batch', 2]}, {'path': '/y', 'shape': ['batch']}]


@pytest.mark.parametrize(('schema', 'case'), [
    pytest.param(group['schema'], case, id=case['description'])
    for group in CASES for case in group['tests']
])
def test_conformance(schema, case):
    errors = SchemaEngine().errors({**ML, **schema}, case['data'])
    assert (not errors) == case['valid']
    if errors:
        assert errors[0]['keyword'] == 'tensorShapes'


@pytest.mark.parametrize('rules', [
    [], [{'path': ''}], [{'path': '/bad~2', 'shape': []}],
    [{'path': '', 'shape': [-1]}], [{'path': '', 'shape': [1.5]}],
    [{'path': '', 'shape': [True]}], [{'path': '', 'shape': ['batch size']}],
    [{'path': '', 'shape': ['batch\n']}], [{'path': '', 'shape': [], 'dtype': 'float32'}],
])
def test_rejects_malformed_nested_schema(rules):
    Draft202012Validator.check_schema(META_SCHEMA)
    with pytest.raises(ValueError, match='Invalid JSON Schema'):
        check_schema({**ML, '$defs': {'tensor': {'tensorShapes': rules}}, '$ref': '#/$defs/tensor'})


@pytest.mark.parametrize('dialect', [{}, {'$schema': RELATIONSHIPS_DIALECT}])
def test_keywords_require_ml_profile(dialect):
    with pytest.raises(ValueError, match='tensorShapes requires'):
        check_schema({**dialect, 'tensorShapes': TENSORS})
    check_schema({**dialect, 'const': {'tensorShapes': TENSORS}})


def test_relationship_keywords_are_separate():
    with pytest.raises(ValueError, match='uniqueKeys requires'):
        check_schema({**ML, 'uniqueKeys': ['']})


def test_local_reference_scope_and_diagnostics():
    schema = {
        **ML, '$defs': {'pair': {'tensorShapes': TENSORS}},
        'items': {'$ref': '#/$defs/pair'},
    }
    engine = SchemaEngine()
    first = {'x': [[1, 2]], 'y': [1]}
    second = {'x': [[1, 2], [3, 4]], 'y': [1, 2]}
    assert not engine.errors(schema, [first, second])
    error, = engine.errors(schema, [first, {**second, 'y': [1]}])
    assert error['instanceLocation'] == '/1/y'
    assert error['schemaLocation'] == '/$defs/pair/tensorShapes'
    assert not engine.errors(schema, [first, second])


def test_standard_schema_can_require_numeric_leaves():
    schema = {**ML, 'tensorShapes': [{'path': '', 'shape': [2]}], 'items': {'type': 'number'}}
    assert not SchemaEngine().errors(schema, [0.5, 1])
    error, = SchemaEngine().errors(schema, ['1', 1])
    assert error['keyword'] == 'type'


@pytest.mark.parametrize('kind', ['document', 'tool_envelope'])
def test_contract_runtime(kind):
    schema = {**ML, 'type': 'object', 'tensorShapes': TENSORS}
    contract = Contract(id='batch', version='1', schema=schema, outputKind=kind,
                        tool='batch' if kind == 'tool_envelope' else None)

    def output(labels):
        doc = {'x': [[1, 2], [3, 4]], 'y': labels}
        return doc if kind == 'document' else {
            'action': 'call_tool', 'tool': 'batch', 'arguments': doc,
            'missingFields': [], 'reason': '',
        }

    engine = SchemaEngine()
    assert validate_contract(output([0, 1]), engine, contract)['accepted']
    assert not validate_contract(output([0]), engine, contract)['accepted']


@pytest.mark.asyncio
async def test_unsupported_native_routes_reject_ml():
    schema = {**ML, 'tensorShapes': TENSORS}
    with pytest.raises(ValueError, match='Blaze does not support'):
        SchemaEngine(backend='blaze').register(schema)
    provider = Provider('mock', 'mock')
    try:
        with pytest.raises(ProviderError, match='use prompt_only') as error:
            await provider.generate([], format_schema=schema)
        assert error.value.requests == 0
    finally:
        await provider.close()
