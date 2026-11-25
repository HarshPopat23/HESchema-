"""The original fifteen audit cases exercised through the public SchemaEngine."""

import json

import pytest

from heschema.assert_expression import DIALECT
from heschema.jsonio import loads
from heschema.schema import SchemaEngine, check_schema


def lit(value):
    return {'literal': value}


def get(path='', name='root'):
    return {'get': {'from': name, 'path': path}}


def dec(value):
    return {'decimal': value}


def run(expression, data=None):
    return SchemaEngine().errors({'$schema': DIALECT, 'assertExpression': expression}, data)


def test_gap_01_arbitrary_keys():
    data = {'a.b': 1, 'a': {'b': 2}, '': 3, '~/': 4}
    for path, expected in [('/a.b', 1), ('/a/b', 2), ('/', 3), ('/~0~1', 4)]:
        assert not run({'eq': [get(path), lit(expected)]}, data)
        assert run({'ne': [get(path), lit(expected)]}, data)


def test_gap_02_literal_json_objects():
    expression = {'eq': [lit({'unknown': [None, True, {'get': 'data'}]}), get()]}
    assert not run(expression, {'unknown': [None, True, {'get': 'data'}]})
    assert run(expression, {'unknown': []})


def test_gap_03_presence():
    exists = {'exists': {'from': 'root', 'path': '/x'}}
    assert not run(exists, {'x': None})
    assert not run(exists, {'x': ''})
    assert run(exists, {})[0]['reasonCode'] == 'ASSERT_EXPRESSION_FALSE'
    assert run({'eq': [get('/x'), lit(None)]}, {})[0]['reasonCode'] == 'ASSERT_EXPRESSION_ERROR'


def test_gap_04_structural_equality():
    assert not run({'eq': [lit({'b': [1, 2], 'a': 0}), lit({'a': 0.0, 'b': [1.0, 2]})]})
    assert run({'eq': [lit({'a': True}), lit({'a': 1})]})
    assert run({'eq': [lit([1, 2]), lit([2, 1])]})


def test_gap_05_nested_parent_binding():
    expression = {'all': {'array': get('/groups'), 'as': 'group', 'test': {
        'all': {'array': get('/items', 'group'), 'as': 'item', 'test': {
            'and': [
                {'lte': [get('/value', 'item'), get('/limit', 'group')]},
                {'lte': [get('/value', 'item'), get('/maximum')]},
            ],
        }},
    }}}
    assert not run(expression, {'maximum': 5, 'groups': [{'limit': 3, 'items': [{'value': 2}]}]})
    assert run(expression, {'maximum': 5, 'groups': [{'limit': 3, 'items': [{'value': 4}]}]})


def test_gap_06_dynamic_regex():
    expression = {'matches': [get('/text'), get('/pattern')]}
    assert not run(expression, {'text': 'AB12', 'pattern': '^[A-Z]+[0-9]+$'})
    assert run(expression, {'text': '12AB', 'pattern': '^[A-Z]+[0-9]+$'})
    error = run(expression, {'text': 'x', 'pattern': '(?=x)'})[0]
    assert error['reasonCode'] == 'ASSERT_EXPRESSION_ERROR'
    assert error['instanceLocation'] == '/pattern'


def test_gap_07_dates_and_instants():
    assert not run({'lt': [{'timestamp': lit('2025-01-01T00:30:00+01:00')},
                          {'timestamp': lit('2025-01-01T00:00:00Z')}]})
    assert not run({'eq': [{'timestamp': lit('2025-01-01T00:30:00+01:00')},
                          {'timestamp': lit('2024-12-31T23:30:00Z')}]})
    assert run({'eq': [{'date': get()}, {'date': lit('2025-03-01')}]}, '2025-02-29')
    assert not run({'lt': [{'date': lit('2024-02-29')}, {'date': lit('2024-03-01')}]})
    assert run({'eq': [{'timestamp': get()}, {'timestamp': lit('2025-03-01T00:00:00Z')}]},
               '2025-03-01')


def test_gap_08_exact_decimals_and_rounding():
    assert not run({'eq': [{'add': [dec('0.10'), dec('0.20')]}, dec('0.30')]})
    assert run({'eq': [{'add': [dec('0.10'), dec('0.20')]}, dec('0.31')]})
    for mode, expected in [('half-even', '-2.50'), ('half-up', '-2.51'), ('toward-zero', '-2.50')]:
        assert not run({'eq': [{'round': {'value': dec('-2.505'), 'scale': 2, 'mode': mode}},
                              dec(expected)]})
    assert not run({'eq': [{'round': {'value': {'divide': [dec('1'), dec('3')]},
                                     'scale': 2, 'mode': 'half-even'}}, dec('0.33')]})
    assert run({'eq': [{'divide': [dec('1'), dec('0')]}, dec('0')]})


def test_gap_09_large_integers_from_json_text():
    data = loads('{"a":9007199254740992,"b":9007199254740993}')
    assert not run({'lt': [get('/a'), get('/b')]}, data)
    assert run({'eq': [get('/a'), get('/b')]}, data)
    assert not run({'eq': [{'toInteger': lit('9007199254740993')}, get('/b')]}, data)


def test_gap_10_code_points_and_graphemes():
    assert not run({'eq': [{'slice': {'value': lit('😀X'), 'start': 0, 'end': 1,
                                     'unit': 'codePoint'}}, lit('😀')]})
    assert not run({'eq': [{'slice': {'value': lit('e\u0301X'), 'start': 0, 'end': 1,
                                     'unit': 'grapheme'}}, lit('e\u0301')]})
    assert not run({'eq': [{'length': lit('😀X')}, lit(2)]})
    assert run({'eq': [{'slice': {'value': get(), 'start': 0, 'end': 4,
                                 'unit': 'codePoint'}}, lit('x')]}, 'x')


def test_gap_11_diagnostics_through_local_reference():
    schema = {'$schema': DIALECT, '$defs': {'rule': {'assertExpression': {
        'all': {'array': get('/items'), 'as': 'item', 'test': {
            'lte': [get('/quantity', 'item'), get('/limit')],
        }},
    }}}, 'items': {'$ref': '#/$defs/rule'}}
    error = SchemaEngine().errors(schema, [{'limit': 3, 'items': [{'quantity': 4}]}])[0]
    assert error['reasonCode'] == 'ASSERT_EXPRESSION_FALSE'
    assert error['instanceLocation'] == '/0/items/0/quantity'
    assert error['schemaLocation'] == '/$defs/rule/assertExpression'
    assert error['expressionLocation'] == '/$defs/rule/assertExpression/all/test/lte'
    assert run({'not': get('/missing')}, {})[0]['instanceLocation'] == '/missing'


@pytest.mark.parametrize('bad', [
    {'unknown': []}, {'eq': [lit(1)]}, {'not': lit(1)},
    {'lt': [lit('4'), lit(5)]}, {'get': {'from': 'unbound', 'path': ''}},
    {'get': {'from': 'root', 'path': '/~2'}},
    {'slice': {'value': lit(1), 'start': 0, 'end': 1, 'unit': 'codePoint'}},
    {'round': {'value': dec('1'), 'scale': True, 'mode': 'half-even'}},
    {'matches': [lit('x'), lit('(?=x)')]},
])
def test_gap_12_reject_invalid_untaken_branch(bad):
    with pytest.raises(ValueError):
        check_schema({'$schema': DIALECT, 'assertExpression': {
            'if': {'test': lit(True), 'then': lit(True), 'else': bad},
        }})


def test_gap_13_empty_arrays():
    for op, valid in [('all', True), ('some', False)]:
        assert (not run({op: {'array': lit([]), 'as': 'x', 'test': lit(True)}})) == valid


def test_gap_14_strict_dynamic_types_and_conversions():
    for value in ['4', None, True]:
        assert run({'lt': [get(), lit(5)]}, value)[0]['reasonCode'] == 'ASSERT_EXPRESSION_ERROR'
    assert not run({'lt': [{'toInteger': lit('4')}, lit(5)]})
    for value in ['4kg', ' 4', '+4', '04', 4.2]:
        assert run({'eq': [{'toInteger': get()}, lit(4)]}, value)


def test_gap_15_json_defined_lazy_function():
    expression = {'define': {
        'name': 'choose', 'params': ['condition', 'yes', 'no'],
        'body': {'if': {'test': get('', 'condition'), 'then': get('', 'yes'), 'else': get('', 'no')}},
        'in': {'call': {'name': 'choose', 'args': [lit(True), lit(True), {
            'eq': [{'divide': [dec('1'), dec('0')]}, dec('1')],
        }]}},
    }}
    assert not run(expression)
    expression['define']['in']['call']['args'][0] = lit(False)
    assert run(expression)[0]['reasonCode'] == 'ASSERT_EXPRESSION_ERROR'


def test_function_specialization_checks_dead_branches():
    expression = {'define': {'name': 'negative', 'params': ['x'],
                            'body': {'lt': [get('', 'x'), lit(0)]},
                            'in': {'call': {'name': 'negative', 'args': [lit('wrong')]}}}}
    with pytest.raises(ValueError):
        check_schema({'$schema': DIALECT, 'assertExpression': expression})


def test_functions_cannot_recurse_or_capture_callers_binding():
    with pytest.raises(ValueError):
        check_schema({'$schema': DIALECT, 'assertExpression': {'define': {
            'name': 'recursive', 'params': [], 'body': {'call': {'name': 'recursive', 'args': []}},
            'in': lit(True),
        }}})
    expression = {'define': {'name': 'read', 'params': [], 'body': get('/limit'),
                            'in': {'all': {'array': get('/items'), 'as': 'item',
                                           'test': {'eq': [{'call': {'name': 'read', 'args': []}},
                                                           get('', 'item')]}}}}}
    assert not run(expression, {'limit': 3, 'items': [3, 3]})


def test_string_limits_and_decimal_precision():
    assert run({'matches': [lit('x'), get()]}, 'x' * 1001)
    assert run({'matches': [get(), lit('x')]}, 'x' * 100001)
    assert run({'eq': [{'decimal': get()}, dec('1')]}, '1e0')
    assert run({'eq': [{'decimal': get()}, dec('1')]}, '9' * 39)
    assert run({'eq': [{'toInteger': get()}, lit(0)]}, '9' * 1001)


def test_assertion_syntax_is_serializable_json():
    # Encoded rules and instances use the same strict ingestion path as the CLI.
    schema = loads(json.dumps({'$schema': DIALECT, 'assertExpression': {
        'eq': [{'add': [dec('0.1'), dec('0.2')]}, dec('0.3')],
    }}))
    assert not SchemaEngine().errors(schema, loads('{}'))


def test_static_union_retains_known_bad_branch():
    with pytest.raises(ValueError):
        check_schema({'$schema': DIALECT, 'assertExpression': {
            'if': {'test': lit(True), 'then': lit(1), 'else': get('/dynamic')},
        }})


def test_decimal_operations_and_timestamp_fraction():
    assert not run({'eq': [{'subtract': [dec('0.30'), dec('0.10')]}, dec('0.20')]})
    assert not run({'eq': [{'multiply': [dec('0.10'), dec('3')]}, dec('0.30')]})
    assert not run({'lt': [{'timestamp': lit('2025-01-01T00:00:00.000000001Z')},
                          {'timestamp': lit('2025-01-01T00:00:00.000000002Z')}]})
    assert not run({'eq': [{'timestamp': lit('2025-01-01T00:00:00.10Z')},
                          {'timestamp': lit('2025-01-01T00:00:00.1Z')}]})
    for value in ['2025-01-01T24:00:00Z', '2025-01-01T00:00:60Z', '2025-01-01T00:00:00']:
        assert run({'eq': [{'timestamp': get()}, {'timestamp': lit('2025-01-01T00:00:00Z')}]}, value)


def test_macro_argument_uses_callers_scope_and_parent_bindings():
    expression = {'define': {'name': 'identity', 'params': ['x'], 'body': get('', 'x'),
                            'in': {'all': {'array': get('/flags'), 'as': 'flag',
                                           'test': {'call': {'name': 'identity',
                                                             'args': [get('', 'flag')]}}}}}}
    assert not run(expression, {'flags': [True, True]})
    assert run(expression, {'flags': [True, False]})


def test_repeated_lazy_arguments_share_budget():
    body = lit(True)
    for _ in range(12):
        body = {'define': {'name': f'twice{_}', 'params': [f'x{_}'],
                           'body': {'and': [get('', f'x{_}'), get('', f'x{_}')]},
                           'in': {'call': {'name': f'twice{_}', 'args': [body]}}}}
    result = run(body)
    assert result and result[0]['reasonCode'] == 'ASSERT_EXPRESSION_ERROR'


def test_json_bounds_and_surrogates_are_controlled_errors():
    assert run(lit(True), {'text': '\ud800'})[0]['reasonCode'] == 'ASSERT_EXPRESSION_ERROR'
    value = []
    for _ in range(50):
        value = [value]
    assert run(lit(True), value)[0]['reasonCode'] == 'ASSERT_EXPRESSION_ERROR'


def test_published_conformance_corpus():
    from pathlib import Path

    corpus = loads((Path(__file__).parents[1] / 'vocabulary/assert-expression/v1/cases.json').read_text())
    assert {group['gap'] for group in corpus['groups']} == set(range(1, 16))
    for group in corpus['groups']:
        for case in group['tests']:
            data = loads(json.dumps(case['data']))
            assert (not run(group['expression'], data)) == case['valid'], group['description']
    for case in corpus['schemaTests']:
        with pytest.raises(ValueError):
            check_schema({'$schema': DIALECT, 'assertExpression': case['expression']})


def test_vocabulary_and_website_examples_match_implementation():
    import ast
    import re
    from pathlib import Path

    from heschema.assert_expression import META_SCHEMA, META_VALIDATOR, check_expression

    root = Path(__file__).parents[1]
    document = (root / 'vocabulary/assert-expression/v1/README.md').read_text()
    for language, code in re.findall(r'```(json|python)\n(.*?)\n```', document, re.S):
        if language == 'python':
            ast.parse(code)
            continue
        value = loads(code)
        if '$schema' in value:
            check_schema(value)
        elif len(value) == 1:
            # Fragments can return any type as operands of a Boolean assertion.
            check_expression(value)
    assert META_VALIDATOR.is_valid({'assertExpression': {'eq': [lit(1), lit(1)]}})
    assert not META_VALIDATOR.is_valid({'assertExpression': {'eq': [lit(1)]}})
    assert META_SCHEMA['$defs']['expression']
    source = (root / 'heschema-web/src/data/assertExpressionDocs.js').read_text()
    website = loads(source.removeprefix('export const ASSERT_EXPRESSION_PAGES = ').strip().removesuffix(';'))
    expected = document.split('\n', 1)[1].replace(
        '[conformance corpus](cases.json)',
        '[conformance corpus](https://github.com/HarshPopat23/HESchema-/blob/main/vocabulary/assert-expression/v1/cases.json)',
    )
    assert website['kw-assertExpression']['content'] == expected


def test_predicate_type_error_points_to_the_item():
    error = run({'all': {'array': get('/items'), 'as': 'item', 'test': get('', 'item')}},
                {'items': [True, 3]})[0]
    assert error['reasonCode'] == 'ASSERT_EXPRESSION_ERROR'
    assert error['instanceLocation'] == '/items/1'
