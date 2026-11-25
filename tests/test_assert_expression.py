import pytest

from heschema.assert_expression import DIALECT
from heschema.schema import SchemaEngine, check_schema


def literal(value):
    return {'literal': value}


def get(path, name='root'):
    return {'get': {'from': name, 'path': path}}


def errors(expression, data):
    return SchemaEngine().errors({'$schema': DIALECT, 'assertExpression': expression}, data)


@pytest.mark.parametrize(('expression', 'data', 'valid'), [
    ({'eq': [get('/a.b'), literal(2)]}, {'a.b': 2}, True),
    ({'eq': [get('/'), literal('empty')]}, {'': 'empty'}, True),
    ({'exists': {'from': 'root', 'path': '/x'}}, {'x': None}, True),
    ({'exists': {'from': 'root', 'path': '/x'}}, {'x': ''}, True),
    ({'exists': {'from': 'root', 'path': '/x'}}, {}, False),
    ({'eq': [literal({'x': [1]}), literal({'x': [1.0]})]}, {}, True),
    ({'eq': [literal(True), literal(1)]}, {}, False),
    ({'eq': [literal([1, 2]), literal([2, 1])]}, {}, False),
    ({'eq': [literal(9007199254740992), literal(9007199254740993)]}, {}, False),
    ({'lt': [get('/a'), get('/b')]}, {'a': 1, 'b': 2}, True),
    ({'lte': [literal(2), literal(2)]}, {}, True),
    ({'gt': [literal(3), literal(2)]}, {}, True),
    ({'gte': [literal(2), literal(2)]}, {}, True),
    ({'ne': [literal('a'), literal('b')]}, {}, True),
    ({'not': literal(False)}, {}, True),
    ({'and': [literal(False), get('/absent')]}, {}, False),
    ({'or': [literal(True), get('/absent')]}, {}, True),
    ({'if': {'test': literal(True), 'then': literal(True), 'else': get('/absent')}}, {}, True),
])
def test_expression_results(expression, data, valid):
    assert (not errors(expression, data)) == valid


def test_root_binding_inside_predicate():
    expression = {'all': {
        'array': get('/items'), 'as': 'item',
        'test': {'lte': [get('/quantity', 'item'), get('/limit')]},
    }}
    assert not errors(expression, {'limit': 3, 'items': [{'quantity': 2}]})
    result = errors(expression, {'limit': 3, 'items': [{'quantity': 4}]})
    assert result[0]['keyword'] == 'assertExpression'
    assert result[0]['instanceLocation'] == ''
    assert 'ASSERT_EXPRESSION_FALSE' in result[0]['message']
    assert not errors(expression, {'limit': 3, 'items': []})


def test_some_empty_and_matching_arrays():
    expression = {'some': {'array': get(''), 'as': 'x', 'test': get('', 'x')}}
    assert errors(expression, [])
    assert not errors(expression, [False, True])


@pytest.mark.parametrize('expression', [
    {'unknown': []}, {'eq': [literal(1)]},
    {'get': {'from': 'root', 'path': '/bad~2'}},
    {'get': {'from': 'missing', 'path': ''}},
    {'if': {'test': literal(True), 'then': literal(True), 'else': {'unknown': []}}},
    {'all': {'array': get(''), 'as': 'root', 'test': literal(True)}},
    {'all': {'array': get(''), 'as': [], 'test': literal(True)}},
])
def test_registration_rejects_bad_rules_in_nested_schema(expression):
    with pytest.raises(ValueError, match='Invalid assertExpression'):
        check_schema({'$schema': DIALECT, 'items': {'assertExpression': expression}})


@pytest.mark.parametrize('expression', [
    literal(1),
    {'lt': [literal('4'), literal(5)]},
    {'lt': [literal(True), literal(5)]},
    get('/missing'),
    {'all': {'array': literal(3), 'as': 'x', 'test': literal(True)}},
])
def test_runtime_errors_are_distinct(expression):
    assert 'ASSERT_EXPRESSION_ERROR' in errors(expression, {})[0]['message']


def test_budget_and_depth():
    expression = {'all': {'array': get(''), 'as': 'x', 'test': literal(True)}}
    assert 'budget exceeded' in errors(expression, [0] * 10001)[0]['message']
    expression = literal(True)
    for _ in range(50):
        expression = {'not': expression}
    with pytest.raises(ValueError, match='nesting'):
        check_schema({'$schema': DIALECT, 'assertExpression': expression})


def test_reference_scope_and_literal_schema_data():
    schema = {'$schema': DIALECT, '$defs': {
        'item': {'assertExpression': {'eq': [get('/a'), get('/b')]}}
    }, 'items': {'$ref': '#/$defs/item'}}
    result = SchemaEngine().errors(schema, [{'a': 1, 'b': 2}])
    assert result[0]['instanceLocation'] == '/0'
    assert not SchemaEngine().errors(schema, [{'a': 1, 'b': 1}])
    check_schema({'const': {'assertExpression': {'unknown': []}}})
    with pytest.raises(ValueError, match='requires'):
        check_schema({'assertExpression': literal(True)})
