"""Small deterministic application rules, not a JSON Schema vocabulary or expression evaluator."""

import re
from datetime import date
from math import isfinite, prod

from .diagnostics import diagnostic, parts, resolve

KINDS = {'product_equals', 'sum_equals', 'date_before', 'equals', 'reference_member'}


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
    ids = set()
    for rule in rules:
        if rule.get('kind') not in KINDS or not rule.get('id') or rule['id'] in ids:
            raise ValueError('Relationship rules require distinct IDs and a supported kind')
        ids.add(rule['id'])
        allowed = {'id', 'kind', 'operands', 'target', 'left', 'right', 'contextLocation'}
        if set(rule) - allowed:
            raise ValueError('Unknown relationship rule option')
        if rule['kind'] in {'product_equals', 'sum_equals'}:
            if not isinstance(rule.get('operands'), list) or not rule['operands']:
                raise ValueError('Arithmetic rule requires nonempty operand pointers')
            for p in [*rule['operands'], rule['target']]:
                parts(p)
        elif rule['kind'] == 'reference_member':
            parts(rule['target'])
            parts(rule['contextLocation'])
        else:
            parts(rule['left'])
            parts(rule['right'])


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


def evaluate_rules(document, rules, context=None, trusted_locations=None):
    errors, records = [], []
    for rule in rules:
        kind, rule_id = rule['kind'], rule['id']
        location = rule.get('target', rule.get('left', ''))
        try:
            if kind in {'product_equals', 'sum_equals'}:
                operands = [resolve(document, p) for p in rule['operands']]
                actual = resolve(document, rule['target'])
                operands = [_integer(v) for v in operands]
                actual = _integer(actual)
                expected = prod(operands) if kind == 'product_equals' else sum(operands)
                valid = actual == expected
            elif kind == 'date_before':
                actual, expected = resolve(document, rule['left']), resolve(document, rule['right'])
                valid = _date(actual) < _date(expected)
            elif kind == 'equals':
                actual, expected = resolve(document, rule['left']), resolve(document, rule['right'])
                valid = json_equal(actual, expected)
            else:
                actual = resolve(document, rule['target'])
                if context is None or (trusted_locations is not None and rule['contextLocation'] not in trusted_locations):
                    raise KeyError('context')
                expected = resolve(context, rule['contextLocation'])
                if not isinstance(expected, list):
                    raise ValueError('Reference membership requires a trusted array')
                valid = any(json_equal(actual, item) for item in expected)
            records.append({'ruleId': rule_id, 'status': 'valid' if valid else 'invalid'})
            if not valid:
                errors.append(diagnostic('RELATION_MISMATCH', 'relationships', location,
                                         f'{kind} failed', ruleId=rule_id, actual=actual, expected=expected))
        except KeyError:
            records.append({'ruleId': rule_id, 'status': 'needs_context'})
            errors.append(diagnostic('RELATION_INPUT_MISSING', 'relationships', location,
                                     'Required rule evidence is missing', ruleId=rule_id, repair='needs_context'))
        except (ValueError, TypeError) as exc:
            records.append({'ruleId': rule_id, 'status': 'invalid'})
            errors.append(diagnostic('RELATION_TYPE_INVALID', 'relationships', location, str(exc), ruleId=rule_id))
    status = 'needs_context' if any(r['status'] == 'needs_context' for r in records) else 'invalid' if errors else 'valid' if rules else 'not_evaluated'
    return {'status': status, 'rules': records, 'errors': errors, 'implementation': 'application_rules'}
