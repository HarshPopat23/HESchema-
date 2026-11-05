"""Dense JSON tensor assertions for the standalone ML dialect."""

import json
from importlib.resources import files
from math import isfinite

from jsonschema import Draft202012Validator, ValidationError, validators

from .diagnostics import parts, resolve
from .unique_keys import FIELD_COMPARISON_REGISTRY

META_SCHEMA = json.loads(files('heschema').joinpath('ml-v1.json').read_text(encoding='utf-8'))
DIALECT = META_SCHEMA['$id']
META_VALIDATOR = Draft202012Validator(META_SCHEMA, registry=FIELD_COMPARISON_REGISTRY)


def _children(array, path, axis):
    for index, item in enumerate(array):
        yield item, (*path, index), axis + 1


def _check_shape(value, path, shape, symbols):
    observed = [None] * len(shape)
    stack = [iter(((value, path, 0),))]
    while stack:
        node = next(stack[-1], None)
        if node is None:
            stack.pop()
            continue
        value, path, axis = node
        if axis == len(shape):
            if type(value) not in {int, float, str, bool} or (
                type(value) is float and not isfinite(value)
            ):
                raise ValidationError('Expected a tensor scalar at the declared rank', path=path)
            continue
        if not isinstance(value, list):
            raise ValidationError(f'Expected a tensor array at axis {axis}', path=path)

        size = len(value)
        dimension = shape[axis]
        if isinstance(dimension, str):
            expected = symbols.setdefault(dimension, size)
            if size != expected:
                raise ValidationError(
                    f'Dimension {dimension!r} expects {expected} at axis {axis}, got {size}', path=path,
                )
        elif dimension is not None and size != dimension:
            raise ValidationError(f'Expected size {dimension} at axis {axis}, got {size}', path=path)
        if observed[axis] is None:
            observed[axis] = size
        elif size != observed[axis]:
            raise ValidationError(
                f'Ragged tensor at axis {axis}: expected {observed[axis]}, got {size}', path=path,
            )
        if value:
            stack.append(_children(value, path, axis))


def _tensor_shapes(_validator, tensors, instance, _schema):
    symbols = {}
    for tensor in tensors:
        location = tensor['path']
        path = tuple(parts(location))
        try:
            value = resolve(instance, location)
        except (KeyError, ValueError):
            yield ValidationError(f'Tensor pointer {location!r} could not be resolved', path=path)
            return
        try:
            _check_shape(value, path, tensor['shape'], symbols)
        except ValidationError as error:
            yield error
            return


VALIDATOR = validators.extend(Draft202012Validator, {'tensorShapes': _tensor_shapes})
