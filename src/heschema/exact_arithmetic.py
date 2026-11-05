"""Exact decimal arithmetic assertions for Relationships v4."""

import json
import operator
import re
from fractions import Fraction
from importlib.resources import files

from jsonschema import Draft202012Validator, ValidationError, validators
from referencing import Resource

from . import ordering
from .diagnostics import parts, resolve

META_SCHEMA = json.loads(files('heschema').joinpath('relationships-v4.json').read_text(encoding='utf-8'))
DIALECT = META_SCHEMA['$id']
META_VALIDATOR = Draft202012Validator(
    META_SCHEMA, registry=ordering.META_REGISTRY.with_resource(
        ordering.DIALECT, Resource.from_contents(ordering.META_SCHEMA),
    ),
)

_MAX_DIGITS = 38
_MAX_SCALE = 18
_DECIMAL = re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]{1,18})?')
_OPERATIONS = {
    'add': operator.add,
    'subtract': operator.sub,
    'multiply': operator.mul,
    'divide': operator.truediv,
    'percentOf': lambda amount, rate: amount * rate / 100,
}


def _decimal_at(instance, location):
    path = parts(location)
    try:
        value = resolve(instance, location)
    except (KeyError, ValueError):
        raise ValidationError(f'Could not resolve decimal pointer {location!r}', path=path) from None
    if (not isinstance(value, str) or len(value) > _MAX_DIGITS + 2
            or not _DECIMAL.fullmatch(value)
            or len(value.removeprefix('-').replace('.', '')) > _MAX_DIGITS):
        raise ValidationError(
            'Expected a decimal string with at most 38 digits and 18 fractional digits', path=path,
        )
    return Fraction(value)


def _round(value, scale, mode):
    # JSON Schema accepts integral number spellings such as 2.0 for the scale.
    factor = 10 ** int(scale)
    magnitude = abs(value) * factor
    quotient, remainder = divmod(magnitude.numerator, magnitude.denominator)
    if mode != 'toward-zero':
        twice = 2 * remainder
        if twice > magnitude.denominator or (
            twice == magnitude.denominator and (mode == 'half-up' or quotient % 2)
        ):
            quotient += 1
    return Fraction(-quotient if value < 0 else quotient, factor)


def _fits_decimal(value):
    scaled = value * 10 ** _MAX_SCALE
    if scaled.denominator != 1:
        return False
    coefficient, scale = abs(scaled.numerator), _MAX_SCALE
    while scale and coefficient % 10 == 0:
        coefficient //= 10
        scale -= 1
    # Zero before the decimal point also counts toward the lexical limit.
    return max(len(str(coefficient)), scale + 1) <= _MAX_DIGITS


def _arithmetic_equals(_validator, rules, instance, _schema):
    for index, rule in enumerate(rules):
        try:
            left = _decimal_at(instance, rule['left'])
            right = _decimal_at(instance, rule['right'])
            actual = _decimal_at(instance, rule['result'])
        except ValidationError as error:
            yield error
            continue
        operation = rule['operation']
        if operation == 'divide' and right == 0:
            yield ValidationError('Division by zero', path=parts(rule['right']))
            continue
        expected = _OPERATIONS[operation](left, right)
        if 'rounding' in rule:
            rounding = rule['rounding']
            expected = _round(expected, rounding['scale'], rounding['mode'])
        result_path = parts(rule['result'])
        if not _fits_decimal(expected):
            yield ValidationError(
                'Computed result is outside the decimal precision or magnitude limits', path=result_path,
            )
        elif actual != expected:
            yield ValidationError(f'Arithmetic rule {index} failed ({operation})', path=result_path)


VALIDATOR = validators.extend(ordering.VALIDATOR, {'arithmeticEquals': _arithmetic_equals})
