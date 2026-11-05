"""Keyed uniqueness using ordered tuples of JSON values."""

import json
from importlib.resources import files

from jsonschema import Draft202012Validator, ValidationError, validators
from referencing import Registry, Resource

from .diagnostics import resolve
from .field_comparison import FIELD_COMPARISON_DIALECT, FIELD_COMPARISON_VALIDATOR, META_SCHEMA

RELATIONSHIPS_META_SCHEMA = json.loads(files('heschema').joinpath('relationships-v1.json').read_text(encoding='utf-8'))
RELATIONSHIPS_DIALECT = RELATIONSHIPS_META_SCHEMA['$id']
FIELD_COMPARISON_REGISTRY = Registry().with_resource(
    FIELD_COMPARISON_DIALECT, Resource.from_contents(META_SCHEMA),
)
RELATIONSHIPS_META_VALIDATOR = Draft202012Validator(
    RELATIONSHIPS_META_SCHEMA, registry=FIELD_COMPARISON_REGISTRY,
)
_MISSING = object()


def json_identity(value):
    """Hashable JSON identity, including structural equality and numeric aliases."""
    if isinstance(value, dict):
        return frozenset((key, json_identity(child)) for key, child in value.items())
    if isinstance(value, list):
        return tuple(json_identity(child) for child in value)
    if isinstance(value, bool):
        return (bool, value)
    return value


def _key_part(item, pointer):
    try:
        return json_identity(resolve(item, pointer))
    except (KeyError, ValueError):
        return _MISSING


def _unique_keys(_validator, pointers, instance, _schema):
    if not isinstance(instance, list):
        return
    seen = {}
    for index, item in enumerate(instance):
        key = tuple(_key_part(item, pointer) for pointer in pointers)
        first = seen.setdefault(key, index)
        if first != index:
            yield ValidationError(f'Item {index} has the same key as item {first}', path=(index,))


RELATIONSHIPS_VALIDATOR = validators.extend(
    FIELD_COMPARISON_VALIDATOR, {'uniqueKeys': _unique_keys},
)
