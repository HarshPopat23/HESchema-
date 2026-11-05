import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from heschema.contracts import Contract
from heschema.providers import Provider, ProviderError
from heschema.relationships_v2 import DIALECT, META_SCHEMA
from heschema.schema import SchemaEngine, check_schema
from heschema.unique_keys import RELATIONSHIPS_DIALECT
from heschema.validation import validate_contract

CASES = json.loads(
    (Path(__file__).resolve().parents[1] / 'vocabulary/relationships/v2/cases.json')
    .read_text(encoding='utf-8')
)
V2 = {'$schema': DIALECT}
AGGREGATE = {'left': '/count', 'operator': 'eq', 'right': {'count': '/items'}}
REFERENCE = {
    'source': {'array': '/citations', 'keys': ['/id']},
    'target': {'array': '/sources', 'keys': ['']},
}


@pytest.mark.parametrize(('schema', 'case'), [
    pytest.param(group['schema'], case, id=case['description'])
    for group in CASES for case in group['tests']
])
def test_conformance(schema, case):
    errors = SchemaEngine().errors({**V2, **schema}, case['data'])
    assert (not errors) == case['valid']
    if errors:
        assert errors[0]['keyword'] in {'aggregateCompare', 'localReferences'}


@pytest.mark.parametrize('fragment', [
    {'aggregateCompare': []},
    {'aggregateCompare': [{**AGGREGATE, 'operator': 'between'}]},
    {'aggregateCompare': [{**AGGREGATE, 'left': {'count': '/items', 'sum': '/items'}}]},
    {'aggregateCompare': [{**AGGREGATE, 'right': {'sum': {'array': '/items'}}}]},
    {'localReferences': [{**REFERENCE, 'target': {'array': '/sources', 'keys': ['/bad~2']}}]},
    {'localReferences': [{**REFERENCE, 'target': {'array': '/sources', 'keys': []}}]},
    {'localReferences': [{**REFERENCE, 'target': {'array': '/sources', 'keys': ['/a', '/b']}}]},
    {'uniqueKeys': []},
    {'compareFields': []},
])
def test_rejects_invalid_keyword_in_referenced_subschema(fragment):
    Draft202012Validator.check_schema(META_SCHEMA)
    with pytest.raises(ValueError, match='Invalid JSON Schema'):
        check_schema({**V2, '$defs': {'batch': fragment}, '$ref': '#/$defs/batch'})


@pytest.mark.parametrize('schema', [{}, {'$schema': RELATIONSHIPS_DIALECT}])
def test_v2_keywords_require_v2_opt_in(schema):
    for keyword, rule in [('aggregateCompare', AGGREGATE), ('localReferences', REFERENCE)]:
        with pytest.raises(ValueError, match=f'{keyword} requires'):
            check_schema({**schema, keyword: [rule]})
        check_schema({**schema, 'const': {keyword: [rule]}})


def test_referenced_rules_report_precise_instance_and_schema_locations():
    schema = {
        **V2,
        'properties': {'batch': {'$ref': '#/$defs/batch'}},
        '$defs': {'batch': {
            'localReferences': [REFERENCE],
            'aggregateCompare': [
                {'left': '/total', 'operator': 'eq',
                 'right': {'sum': {'array': '/items', 'item': '/a~1b'}}},
            ],
        }},
    }
    errors = SchemaEngine().errors(schema, {
        'batch': {'citations': [{'id': 'unknown'}], 'sources': ['known'],
                  'items': [{'a/b': False}], 'total': 0},
    })
    assert {(e['instanceLocation'], e['schemaLocation']) for e in errors} == {
        ('/batch/citations/0', '/$defs/batch/localReferences'),
        ('/batch/items/0/a~1b', '/$defs/batch/aggregateCompare'),
    }


def test_exact_sum_comparison_and_safe_float_boundary():
    schema = {**V2, 'aggregateCompare': [{
        'left': {'sum': {'array': '/amounts', 'item': ''}}, 'operator': 'gt',
        'right': '/limit',
    }]}
    engine = SchemaEngine()
    limit = 2**53
    assert not engine.errors(schema, {'amounts': [limit, 1], 'limit': limit})
    assert engine.errors(schema, {'amounts': [float(limit), 1], 'limit': limit})
    assert engine.errors(schema, {'amounts': [limit], 'limit': limit})


@pytest.mark.parametrize('kind', ['document', 'tool_envelope'])
def test_runtime_enforces_all_four_keywords(kind):
    schema = {
        **V2,
        'type': 'object',
        '$defs': {'sources': {'uniqueKeys': ['']}},
        'properties': {'sources': {'$ref': '#/$defs/sources'}},
        'aggregateCompare': [AGGREGATE],
        'localReferences': [REFERENCE],
        'compareFields': [{'left': '/a', 'right': '/b', 'mode': 'json', 'operator': 'eq'}],
    }
    contract = Contract(id='batch', version='1', schema=schema, outputKind=kind,
                        tool='batch' if kind == 'tool_envelope' else None)
    document = {'sources': ['a'], 'citations': [{'id': 'a'}], 'count': 1,
                'items': [1], 'a': 1, 'b': 1}

    def output(overrides):
        doc = {**document, **overrides}
        return doc if kind == 'document' else {
            'action': 'call_tool', 'tool': 'batch', 'arguments': doc,
            'missingFields': [], 'reason': '',
        }

    engine = SchemaEngine()
    assert validate_contract(output({}), engine, contract)['accepted']
    for invalid in ({'count': 2}, {'citations': [{'id': 'x'}]}, {'sources': ['a', 'a']}, {'b': 2}):
        assert not validate_contract(output(invalid), engine, contract)['accepted']


@pytest.mark.asyncio
async def test_unsupported_native_paths_reject_v2():
    schema = {**V2, 'aggregateCompare': [AGGREGATE]}
    with pytest.raises(ValueError, match='Blaze does not support'):
        SchemaEngine(backend='blaze').register(schema)
    provider = Provider('mock', 'mock')
    try:
        with pytest.raises(ProviderError, match='use prompt_only') as error:
            await provider.generate([], format_schema=schema)
        assert error.value.requests == 0
    finally:
        await provider.close()
