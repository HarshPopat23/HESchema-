"""Boundaries measure schema structure, not a resource-exhaustion exploit."""
import pytest

from heschema.security import check_regex_safety, check_schema_complexity


@pytest.mark.parametrize('wrapper', ['patternProperties', '$defs'])
def test_nested_named_properties_are_counted_once(wrapper):
    child = {'type': 'object', 'properties': {f'p{i}': {'type': 'string'} for i in range(250)}}
    schema = {wrapper: {'^item$' if wrapper == 'patternProperties' else 'item': child}}
    check_schema_complexity(schema, max_properties=250)
    with pytest.raises(ValueError, match='property count'):
        check_schema_complexity(schema, max_properties=249)


def test_reused_schema_object_counts_each_syntactic_occurrence():
    child = {'properties': {'x': {'type': 'string'}}}
    schema = {'patternProperties': {'^a$': child, '^b$': child}}
    check_schema_complexity(schema, max_properties=2)
    with pytest.raises(ValueError, match='property count'):
        check_schema_complexity(schema, max_properties=1)


@pytest.mark.parametrize('keyword', ['properties', 'patternProperties'])
def test_depth_boundary_counts_one_edge_per_schema_child(keyword):
    schema = {keyword: {'x': {'type': 'string'}}}
    check_schema_complexity(schema, max_depth=2)
    with pytest.raises(ValueError, match='depth'):
        check_schema_complexity(schema, max_depth=1)


def test_pattern_keys_are_still_checked_and_regex_length_is_bounded():
    with pytest.raises(ValueError, match='catastrophic'):
        check_schema_complexity({'patternProperties': {'(a+)+$': {'type': 'string'}}})
    check_regex_safety('a' * 1000)
    with pytest.raises(ValueError, match='maximum allowed length'):
        check_regex_safety('a' * 1001)


def test_literal_schema_looking_data_does_not_consume_property_budget():
    check_schema_complexity({'const': {'properties': {str(i): {} for i in range(251)}}}, max_properties=1)
