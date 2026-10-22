"""Small deterministic application rules, not a JSON Schema vocabulary or expression evaluator."""

import re
from datetime import date
from math import isfinite, prod

from .diagnostics import diagnostic, parts, resolve

RULE_POINTERS = {
    'product_equals': ('target',), 'sum_equals': ('target',),
    'division_equals': ('target',), 'percentage_of': ('target',),
    'date_before': ('left', 'right'), 'equals': ('left', 'right'),
    'reference_member': ('target', 'contextLocation'),
    'member_of': ('target', 'arrayLocation'),
    'count_equals': ('target', 'arrayLocation'),
    'sum_items_equals': ('target', 'arrayLocation', 'itemLocation'),
    'unique_by': ('arrayLocation', 'itemLocation'),
}
KINDS = set(RULE_POINTERS)
CALCULABLE_KINDS = {'product_equals', 'sum_equals', 'division_equals', 'percentage_of', 'count_equals', 'sum_items_equals'}


def json_equal(left, right):
    """JSON value equality: numeric aliases match; booleans remain distinct."""
    if type(left) is bool or type(right) is bool:
        return type(left) is type(right) and left == right
    if type(left) in {int, float} and type(right) in {int, float}:
        return left == right
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(json_equal(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(json_equal(a, b) for a, b in zip(left, right))
    return left == right


def check_rules(rules):
    if not isinstance(rules, list):
        raise ValueError('Relationships must be a list')
    ids = set()
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError('Relationship rules must be objects')
        kind, rule_id = rule.get('kind'), rule.get('id')
        if not isinstance(kind, str) or kind not in KINDS or not isinstance(rule_id, str) or not rule_id or rule_id in ids:
            raise ValueError('Relationship rules require distinct IDs and a supported kind')
        ids.add(rule_id)
        required = set(RULE_POINTERS[kind])
        if kind in {'product_equals', 'sum_equals', 'division_equals', 'percentage_of'}:
            required.add('operands')
        options = {'compute', 'precision', 'tolerance'} if kind in CALCULABLE_KINDS else set()
        if set(rule) - options != {'id', 'kind'} | required:
            raise ValueError(f'{kind} requires exactly these options: {sorted(required)}')
        if 'compute' in rule and rule['compute'] not in ('model', 'application'):
            raise ValueError('compute must be model or application')
        if 'precision' in rule:
            if not isinstance(rule['precision'], int) or rule['precision'] < 0:
                raise ValueError('precision must be a non-negative integer')
        if 'tolerance' in rule:
            if not isinstance(rule['tolerance'], (int, float)) or rule['tolerance'] < 0:
                raise ValueError('tolerance must be a non-negative number')
        for key in RULE_POINTERS[kind]:
            parts(rule[key])
        if kind in {'product_equals', 'sum_equals', 'division_equals', 'percentage_of'}:
            if not isinstance(rule.get('operands'), list) or not rule['operands']:
                raise ValueError('Arithmetic rule requires nonempty operand pointers')
            if kind in {'division_equals', 'percentage_of'} and len(rule['operands']) != 2:
                raise ValueError(f'{kind} requires exactly two operand pointers')
            for p in rule['operands']:
                parts(p)


def _date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('Expected YYYY-MM-DD date')
    return date.fromisoformat(value)


def _integer(value):
    if type(value) is int:
        return value
    # JSON Schema integers are semantic numbers. Integral reals are safe only
    # within the exact IEEE-754 integer range used by this parser.
    if type(value) is float and isfinite(value) and value.is_integer() and abs(value) <= 2**53 - 1:
        return int(value)
    raise ValueError('Expected exact integer minor units; booleans, fractions and unsafe reals are not operands')


def _number(value):
    if type(value) is bool:
        raise ValueError('Expected number; booleans are not numeric operands')
    if type(value) in {int, float} and isfinite(value):
        return value
    raise ValueError('Expected finite number; fractions, booleans or non-numeric values are not operands')


def calculation_value(document, rule):
    """One arithmetic implementation shared by checking and opted-in calculation."""
    kind = rule['kind']
    precision = rule.get('precision')
    tolerance = rule.get('tolerance')
    is_float_mode = (precision is not None) or (tolerance is not None) or (kind in {'division_equals', 'percentage_of'})
    parser = _number if is_float_mode else _integer

    if kind in {'product_equals', 'sum_equals'}:
        raw_ops = [resolve(document, p) for p in rule['operands']]
        operands = [parser(x) for x in raw_ops]
        val = prod(operands) if kind == 'product_equals' else sum(operands)
        if precision is not None:
            return round(float(val), precision)
        if is_float_mode:
            return float(val) if any(type(x) is float for x in operands) else int(val)
        return int(val)
    if kind == 'division_equals':
        raw_a = resolve(document, rule['operands'][0])
        raw_b = resolve(document, rule['operands'][1])
        a, b = _number(raw_a), _number(raw_b)
        if b == 0:
            raise ValueError('Division by zero in calculation rule')
        val = a / b
        return round(float(val), precision) if precision is not None else val
    if kind == 'percentage_of':
        raw_rate = resolve(document, rule['operands'][0])
        raw_total = resolve(document, rule['operands'][1])
        rate, total = _number(raw_rate), _number(raw_total)
        val = (rate * total) / 100.0
        return round(float(val), precision) if precision is not None else val
    if kind not in {'count_equals', 'sum_items_equals'}:
        raise ValueError('Unsupported calculation kind')
    items = resolve(document, rule['arrayLocation'])
    if not isinstance(items, list):
        raise ValueError(f'{kind} requires an array at {rule["arrayLocation"]}')
    if kind == 'count_equals':
        return len(items)
    raw_vals = [resolve(item, rule['itemLocation']) for item in items]
    operands = [parser(x) for x in raw_vals]
    val = sum(operands)
    if precision is not None:
        return round(float(val), precision)
    if is_float_mode:
        return float(val) if any(type(x) is float for x in operands) else int(val)
    return int(val)


def evaluate_rules(document, rules, context=None, trusted_locations=None):
    errors, records = [], []
    for rule in rules:
        kind, rule_id = rule['kind'], rule['id']
        location = rule.get('target', rule.get('left', rule.get('arrayLocation', '')))
        input_locations = [rule[k] for k in RULE_POINTERS[kind]] + rule.get('operands', [])
        precision = rule.get('precision')
        tolerance = rule.get('tolerance')
        is_float_mode = (precision is not None) or (tolerance is not None) or (kind in {'division_equals', 'percentage_of'})
        parser = _number if is_float_mode else _integer
        try:
            if kind in {'product_equals', 'sum_equals', 'division_equals', 'percentage_of'}:
                # Preserve existing missing-evidence precedence before type checks.
                for source in rule['operands']:
                    resolve(document, source)
                raw_actual = resolve(document, rule['target'])
                expected = calculation_value(document, rule)
                actual = parser(raw_actual)
                if tolerance is not None:
                    valid = abs(float(actual) - float(expected)) <= float(tolerance)
                elif precision is not None:
                    valid = round(float(actual), precision) == round(float(expected), precision)
                elif type(actual) is int and type(expected) is int:
                    valid = actual == expected
                else:
                    valid = abs(float(actual) - float(expected)) < 1e-9
            elif kind == 'date_before':
                actual, expected = resolve(document, rule['left']), resolve(document, rule['right'])
                valid = _date(actual) < _date(expected)
            elif kind == 'equals':
                actual, expected = resolve(document, rule['left']), resolve(document, rule['right'])
                valid = json_equal(actual, expected)
            elif kind == 'reference_member':
                actual = resolve(document, rule['target'])
                if context is None or (trusted_locations is not None and rule['contextLocation'] not in trusted_locations):
                    raise KeyError('context')
                expected = resolve(context, rule['contextLocation'])
                if not isinstance(expected, list):
                    raise ValueError('Reference membership requires a trusted array')
                valid = any(json_equal(actual, item) for item in expected)
            else:
                items = resolve(document, rule['arrayLocation'])
                if not isinstance(items, list):
                    raise ValueError(f'{kind} requires an array at {rule["arrayLocation"]}')
                if kind == 'member_of':
                    actual, expected = resolve(document, rule['target']), items
                    valid = any(json_equal(actual, item) for item in items)
                elif kind == 'count_equals':
                    actual = _integer(resolve(document, rule['target']))
                    expected = calculation_value(document, rule)
                    valid = actual == expected
                elif kind == 'sum_items_equals':
                    actual = parser(resolve(document, rule['target']))
                    expected = calculation_value(document, rule)
                    if tolerance is not None:
                        valid = abs(float(actual) - float(expected)) <= float(tolerance)
                    elif precision is not None:
                        valid = round(float(actual), precision) == round(float(expected), precision)
                    elif type(actual) is int and type(expected) is int:
                        valid = actual == expected
                    else:
                        valid = abs(float(actual) - float(expected)) < 1e-9
                elif kind == 'unique_by':
                    actual = [resolve(item, rule['itemLocation']) for item in items]
                    expected = 'distinct values at the declared item pointer'
                    valid = all(not any(json_equal(value, other) for other in actual[:i]) for i, value in enumerate(actual))
                else:
                    raise ValueError('Unsupported relationship kind')
            records.append({'ruleId': rule_id, 'kind': kind, 'status': 'valid' if valid else 'invalid'})
            if not valid:
                errors.append(diagnostic('RELATION_MISMATCH', 'relationships', location,
                                         f'{kind} failed; preserve approved inputs and correct the relationship',
                                         ruleId=rule_id, kind=kind, actual=actual, expected=expected,
                                         inputLocations=input_locations))
        except KeyError:
            records.append({'ruleId': rule_id, 'kind': kind, 'status': 'needs_context'})
            errors.append(diagnostic('RELATION_INPUT_MISSING', 'relationships', location,
                                     'Required rule evidence is missing', ruleId=rule_id, kind=kind, repair='needs_context'))
        except (ValueError, TypeError) as exc:
            records.append({'ruleId': rule_id, 'kind': kind, 'status': 'invalid'})
            errors.append(diagnostic('RELATION_TYPE_INVALID', 'relationships', location, str(exc),
                                     ruleId=rule_id, kind=kind, inputLocations=input_locations))
    status = 'needs_context' if any(r['status'] == 'needs_context' for r in records) else 'invalid' if errors else 'valid' if rules else 'not_evaluated'
    return {'status': status, 'rules': records, 'errors': errors, 'implementation': 'application_rules'}
