"""Typed scalar operations used by the JSON expression evaluator."""

import math
import re
from dataclasses import dataclass
from fractions import Fraction

import re2
import regex

from .exact_arithmetic import _fits_decimal, _round
from .ordering import _timestamp
from .rules import calendar_date

MAX_TEXT = 100000
MAX_PATTERN = 1000
MAX_INTEGER_DIGITS = 1000
_DECIMAL = re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]{1,18})?')
_INTEGER = re.compile(r'-?(?:0|[1-9][0-9]*)')


@dataclass(frozen=True)
class Scalar:
    kind: str
    value: object


def decimal(value):
    if (not isinstance(value, str) or len(value) > 40 or not _DECIMAL.fullmatch(value)
            or len(value.removeprefix('-').replace('.', '')) > 38):
        raise ValueError('Expected a decimal string with at most 38 digits and 18 fractional digits')
    return Scalar('decimal', Fraction(value))


def integer(value):
    if type(value) is int:
        result = value
    elif isinstance(value, str) and len(value) <= MAX_INTEGER_DIGITS + 1 and _INTEGER.fullmatch(value):
        result = int(value)
    else:
        raise ValueError('Expected an integer or an entire canonical integer string')
    if abs(result).bit_length() > 3322 or len(str(abs(result))) > MAX_INTEGER_DIGITS:
        raise ValueError('Integer conversion exceeds 1000 digits')
    return result


def finite_number(value):
    return type(value) is int or type(value) is float and math.isfinite(value)


def text(value):
    if not isinstance(value, str) or len(value) > MAX_TEXT:
        raise ValueError('Expected a string of at most 100000 code points')
    if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise ValueError('Strings must contain Unicode scalar values')
    return value


def pattern(value):
    value = text(value)
    if len(value) > MAX_PATTERN:
        raise ValueError('Regex exceeds 1000 code points')
    options = re2.Options()
    options.max_mem = 1 << 20
    options.log_errors = False
    try:
        return re2.compile(value, options=options)
    except re2.error:
        raise ValueError('Invalid or unsupported RE2 pattern') from None


def temporal(value, kind):
    value = text(value)
    if len(value) > 128:
        raise ValueError('Temporal string exceeds 128 characters')
    return Scalar(kind, calendar_date(value) if kind == 'date' else _timestamp(value))


def arithmetic(op, left, right):
    if not isinstance(left, Scalar) or not isinstance(right, Scalar) or (
        left.kind != 'decimal' or right.kind != 'decimal'
    ):
        raise ValueError('Arithmetic operands must be explicit decimals')
    if op == 'divide' and right.value == 0:
        raise ValueError('Division by zero')
    if op == 'add':
        result = left.value + right.value
    elif op == 'subtract':
        result = left.value - right.value
    elif op == 'multiply':
        result = left.value * right.value
    else:
        result = left.value / right.value
    # Rational intermediates permit exact division followed by explicit rounding.
    if result.numerator.bit_length() > 4096 or result.denominator.bit_length() > 4096:
        raise ValueError('Decimal intermediate exceeds 4096 bits')
    return Scalar('decimal', result)


def rounded(value, scale, mode):
    if not isinstance(value, Scalar) or value.kind != 'decimal':
        raise ValueError('Rounding requires a decimal')
    result = _round(value.value, scale, mode)
    if not _fits_decimal(result):
        raise ValueError('Rounded decimal exceeds supported precision')
    return Scalar('decimal', result)


def slice_text(value, start, end, unit):
    value = text(value)
    units = value if unit == 'codePoint' else regex.findall(r'\X', value, timeout=0.05)
    if not 0 <= start <= end <= len(units):
        raise ValueError('Slice bounds must satisfy 0 <= start <= end <= length')
    return ''.join(units[start:end])
