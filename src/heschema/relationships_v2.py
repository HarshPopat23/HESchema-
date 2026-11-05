"""Exact collection aggregates and references within a JSON instance."""

import json
from importlib.resources import files

from jsonschema import Draft202012Validator, ValidationError, validators
from referencing import Resource

from .diagnostics import parts, resolve
from .field_comparison import COMPARISON_OPERATORS
from .rules import exact_integer
from .unique_keys import (
    FIELD_COMPARISON_REGISTRY,
    RELATIONSHIPS_DIALECT,
    RELATIONSHIPS_META_SCHEMA,
    RELATIONSHIPS_VALIDATOR,
    json_identity,
)

META_SCHEMA = json.loads(files('heschema').joinpath('relationships-v2.json').read_text(encoding='utf-8'))
DIALECT = META_SCHEMA['$id']
META_VALIDATOR = Draft202012Validator(
    META_SCHEMA,
    registry=FIELD_COMPARISON_REGISTRY.with_resource(
        RELATIONSHIPS_DIALECT, Resource.from_contents(RELATIONSHIPS_META_SCHEMA),
    ),
)


def _value_at(instance, location, path=()):
    try:
        return resolve(instance, location)
    except (KeyError, ValueError):
        raise ValidationError(f'Could not resolve pointer {location!r}', path=(*path, *parts(location))) from None


def _array_at(instance, location):
    array = _value_at(instance, location)
    if not isinstance(array, list):
        raise ValidationError(f'Expected an array at {location!r}', path=parts(location))
    return array


def _integer_at(instance, location, path=()):
    value = _value_at(instance, location, path)
    try:
        return exact_integer(value)
    except ValueError:
        raise ValidationError('Expected an exact integer operand', path=(*path, *parts(location))) from None


def _aggregate(instance, operand):
    if isinstance(operand, str):
        return _integer_at(instance, operand)
    if 'count' in operand:
        return len(_array_at(instance, operand['count']))
    spec = operand['sum']
    array = _array_at(instance, spec['array'])
    path = parts(spec['array'])
    return sum(_integer_at(item, spec['item'], (*path, index)) for index, item in enumerate(array))


def _aggregate_compare(_validator, comparisons, instance, _schema):
    for index, comparison in enumerate(comparisons):
        try:
            left = _aggregate(instance, comparison['left'])
            right = _aggregate(instance, comparison['right'])
        except ValidationError as error:
            yield error
            continue
        operator = comparison['operator']
        if not COMPARISON_OPERATORS[operator](left, right):
            yield ValidationError(f'Aggregate comparison {index} failed ({operator})')


def _key_rows(instance, side):
    array = _array_at(instance, side['array'])
    path = parts(side['array'])
    for index, item in enumerate(array):
        row_path = (*path, index)
        key = tuple(json_identity(_value_at(item, location, row_path)) for location in side['keys'])
        yield key, row_path


def _local_references(_validator, references, instance, _schema):
    for rule in references:
        targets = set()
        try:
            for key, path in _key_rows(instance, rule['target']):
                if key in targets:
                    yield ValidationError('Reference target key is not unique', path=path)
                targets.add(key)
            for key, path in _key_rows(instance, rule['source']):
                if key not in targets:
                    yield ValidationError('Reference has no matching local target', path=path)
        except ValidationError as error:
            yield error


VALIDATOR = validators.extend(
    RELATIONSHIPS_VALIDATOR,
    {'aggregateCompare': _aggregate_compare, 'localReferences': _local_references},
)
