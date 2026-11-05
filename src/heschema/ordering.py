"""Ordering and interval assertions for Relationships v3."""

import json
import re
from importlib.resources import files
from itertools import pairwise
from math import isfinite

from jsonschema import Draft202012Validator, ValidationError, validators
from referencing import Resource

from . import relationships_v2
from .diagnostics import parts, resolve
from .rules import calendar_date, exact_integer

META_SCHEMA = json.loads(files('heschema').joinpath('relationships-v3.json').read_text(encoding='utf-8'))
DIALECT = META_SCHEMA['$id']
META_REGISTRY = relationships_v2.META_REGISTRY.with_resource(
    relationships_v2.DIALECT, Resource.from_contents(relationships_v2.META_SCHEMA),
)
META_VALIDATOR = Draft202012Validator(META_SCHEMA, registry=META_REGISTRY)


_TIMESTAMP = re.compile(
    r'([0-9]{4}-[0-9]{2}-[0-9]{2})T([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9])'
    r'(?:\.([0-9]+))?(Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])',
)


def _timestamp(value):
    match = _TIMESTAMP.fullmatch(value) if isinstance(value, str) else None
    if not match:
        raise ValueError('Expected a timestamp with seconds and an explicit UTC offset')
    day, hours, minutes, seconds, fraction, offset = match.groups()
    whole = calendar_date(day).toordinal() * 86400 + int(hours) * 3600 + int(minutes) * 60 + int(seconds)
    if offset != 'Z':
        offset_seconds = int(offset[1:3]) * 3600 + int(offset[4:]) * 60
        whole += offset_seconds if offset[0] == '-' else -offset_seconds
    # Decimal fractional digits compare lexically after removing trailing zeros.
    return whole, (fraction or '').rstrip('0')


def _coordinate(value, mode):
    if mode == 'date':
        return calendar_date(value)
    if mode == 'date-time':
        return _timestamp(value)
    if mode == 'number':
        if type(value) is int or (type(value) is float and isfinite(value)):
            return value
        raise ValueError('Expected a finite JSON number')
    offset = exact_integer(value)
    if offset < 0:
        raise ValueError('Expected a nonnegative offset')
    return offset


def _coordinate_at(item, index, location, mode):
    try:
        return _coordinate(resolve(item, location), mode)
    except (KeyError, ValueError):
        raise ValidationError(
            f'Expected a valid {mode} value at item pointer {location!r}',
            path=(index, *parts(location)),
        ) from None


def _sorted_by(_validator, rule, instance, _schema):
    if not isinstance(instance, list):
        return
    key, mode = rule['key'], rule['mode']
    ascending = rule['direction'] == 'ascending'
    allow_ties = rule['ties'] == 'allow'
    previous = None
    try:
        for index, item in enumerate(instance):
            current = _coordinate_at(item, index, key, mode)
            if index:
                ordered = previous < current if ascending else previous > current
                if not ordered and not (allow_ties and previous == current):
                    yield ValidationError(
                        f'Item {index} violates the ordering relative to item {index - 1}',
                        path=(index, *parts(key)),
                    )
                    return
            previous = current
    except ValidationError as error:
        yield error


def _non_overlapping(_validator, rule, instance, _schema):
    if not isinstance(instance, list):
        return
    half_open = rule['bounds'] == 'half-open'
    intervals = []
    try:
        for index, item in enumerate(instance):
            start = _coordinate_at(item, index, rule['start'], rule['mode'])
            end = _coordinate_at(item, index, rule['end'], rule['mode'])
            if start > end:
                yield ValidationError('Interval start exceeds its end', path=(index,))
                return
            if not half_open or start != end:
                intervals.append((start, end, index))
    except ValidationError as error:
        yield error
        return

    intervals.sort(key=lambda interval: interval[0])
    for (_, previous_end, previous_index), (start, _, index) in pairwise(intervals):
        if start < previous_end or (not half_open and start == previous_end):
            yield ValidationError(f'Interval overlaps item {previous_index}', path=(index,))
            return


VALIDATOR = validators.extend(
    relationships_v2.VALIDATOR,
    {'sortedBy': _sorted_by, 'nonOverlapping': _non_overlapping},
)
