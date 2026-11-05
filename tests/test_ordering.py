import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from heschema.contracts import Contract
from heschema.ordering import DIALECT, META_SCHEMA
from heschema.providers import Provider, ProviderError
from heschema.relationships_v2 import DIALECT as V2_DIALECT
from heschema.schema import SchemaEngine, check_schema
from heschema.validation import validate_contract

CASES = json.loads(
    (Path(__file__).resolve().parents[1] / 'vocabulary/relationships/v3/cases.json')
    .read_text(encoding='utf-8')
)
V3 = {'$schema': DIALECT}
ORDER = {'key': '/at', 'mode': 'number', 'direction': 'ascending', 'ties': 'forbid'}
INTERVAL = {'start': '/start', 'end': '/end', 'mode': 'byte-offset', 'bounds': 'half-open'}


@pytest.mark.parametrize(('schema', 'case'), [
    pytest.param(group['schema'], case, id=case['description'])
    for group in CASES for case in group['tests']
])
def test_conformance(schema, case):
    errors = SchemaEngine().errors({**V3, **schema}, case['data'])
    assert (not errors) == case['valid']
    if errors:
        assert errors[0]['keyword'] in {'sortedBy', 'nonOverlapping'}


@pytest.mark.parametrize('fragment', [
    {'sortedBy': {**ORDER, 'key': '/a~2b'}},
    {'sortedBy': {k: v for k, v in ORDER.items() if k != 'ties'}},
    {'sortedBy': {**ORDER, 'direction': 'up'}},
    {'nonOverlapping': {**INTERVAL, 'bounds': 'open'}},
    {'nonOverlapping': {**INTERVAL, 'mode': 'characters'}},
    {'compareFields': []},
    {'uniqueKeys': []},
    {'aggregateCompare': []},
    {'localReferences': [
        {'source': {'array': '/left', 'keys': ['']}, 'target': {'array': '/right', 'keys': ['/a', '/b']}},
    ]},
])
def test_nested_invalid_schema(fragment):
    Draft202012Validator.check_schema(META_SCHEMA)
    with pytest.raises(ValueError, match='Invalid JSON Schema'):
        check_schema({**V3, '$defs': {'records': fragment}, '$ref': '#/$defs/records'})


@pytest.mark.parametrize('dialect', [{}, {'$schema': V2_DIALECT}])
def test_keywords_require_v3_opt_in(dialect):
    for keyword, rule in [('sortedBy', ORDER), ('nonOverlapping', INTERVAL)]:
        with pytest.raises(ValueError, match=f'{keyword} requires'):
            check_schema({**dialect, keyword: rule})
        check_schema({**dialect, 'const': {keyword: rule}})


def test_referenced_ordering_diagnostic():
    schema = {
        **V3,
        '$defs': {'items': {'sortedBy': {**ORDER, 'key': '/a~1b'}}},
        'properties': {'records': {'$ref': '#/$defs/items'}},
    }
    error, = SchemaEngine().errors(schema, {'records': [{'a/b': 2}, {'a/b': 1}]})
    assert error['instanceLocation'] == '/records/1/a~1b'
    assert error['schemaLocation'] == '/$defs/items/sortedBy'


@pytest.mark.parametrize('kind', ['document', 'tool_envelope'])
def test_contract_runtime(kind):
    schema = {
        **V3, 'type': 'object',
        'properties': {'rows': {'sortedBy': ORDER}, 'spans': {'nonOverlapping': INTERVAL}},
        'aggregateCompare': [{'left': {'count': '/rows'}, 'operator': 'eq', 'right': {'count': '/spans'}}],
    }
    contract = Contract(id='timeline', version='1', schema=schema, outputKind=kind,
                        tool='timeline' if kind == 'tool_envelope' else None)

    def output(rows, spans):
        doc = {'rows': rows, 'spans': spans}
        return doc if kind == 'document' else {
            'action': 'call_tool', 'tool': 'timeline', 'arguments': doc,
            'missingFields': [], 'reason': '',
        }

    rows = [{'at': 1}, {'at': 2}]
    spans = [{'start': 0, 'end': 3}, {'start': 3, 'end': 6}]
    engine = SchemaEngine()
    assert validate_contract(output(rows, spans), engine, contract)['accepted']
    for invalid in (output(rows[::-1], spans), output(rows, [{'start': 1, 'end': 4}, spans[0]]),
                    output(rows, spans[:1])):
        assert not validate_contract(invalid, engine, contract)['accepted']


@pytest.mark.asyncio
async def test_native_paths_reject_v3():
    schema = {**V3, 'sortedBy': ORDER}
    with pytest.raises(ValueError, match='Blaze does not support'):
        SchemaEngine(backend='blaze').register(schema)
    provider = Provider('mock', 'mock')
    try:
        with pytest.raises(ProviderError, match='use prompt_only') as error:
            await provider.generate([], format_schema=schema)
        assert error.value.requests == 0
    finally:
        await provider.close()
