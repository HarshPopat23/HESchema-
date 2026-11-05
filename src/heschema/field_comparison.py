"""Draft 2020-12 extension for comparisons within the current instance."""

import json
import operator
from importlib.resources import files
from math import isfinite

from jsonschema import Draft202012Validator, ValidationError, validators

from .diagnostics import resolve
from .rules import calendar_date, json_equal

META_SCHEMA = json.loads(files('heschema').joinpath('field-comparison-v1.json').read_text(encoding='utf-8'))
FIELD_COMPARISON_DIALECT = META_SCHEMA['$id']
META_VALIDATOR = Draft202012Validator(META_SCHEMA)
_OPERATORS = {'eq': operator.eq, 'ne': operator.ne, 'lt': operator.lt,
              'lte': operator.le, 'gt': operator.gt, 'gte': operator.ge}


def _compare_fields(_validator, comparisons, instance, _schema):
    for index, comparison in enumerate(comparisons):
        left_path, right_path = comparison['left'], comparison['right']
        mode, op = comparison['mode'], comparison['operator']
        try:
            left, right = resolve(instance, left_path), resolve(instance, right_path)
        except KeyError as exc:
            yield ValidationError(f'Comparison {index} could not resolve operand {exc.args[0]!r}')
            continue
        except ValueError:
            yield ValidationError(f'Comparison {index} could not resolve an operand')
            continue
        if mode == 'date':
            try:
                left, right = calendar_date(left), calendar_date(right)
            except ValueError:
                yield ValidationError(f'Comparison {index} requires two YYYY-MM-DD calendar dates')
                continue
        elif mode == 'number' and not all(
            type(value) is int or (type(value) is float and isfinite(value))
            for value in (left, right)
        ):
            yield ValidationError(f'Comparison {index} requires two finite JSON numbers')
            continue

        if mode == 'json':
            equal = json_equal(left, right)
            valid = equal if op == 'eq' else not equal
        else:
            valid = _OPERATORS[op](left, right)
        if not valid:
            yield ValidationError(f'Comparison {index} failed: {left_path!r} {op} {right_path!r} ({mode})')


FIELD_COMPARISON_VALIDATOR = validators.extend(
    Draft202012Validator, {'compareFields': _compare_fields},
)
