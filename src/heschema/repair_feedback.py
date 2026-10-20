"""Bounded runtime diagnostics for repairs; no scoring oracle or output mutation."""

from jsonschema import Draft202012Validator

from .diagnostics import parts, pointer, resolve
from .jsonio import canonical
from .rules import json_equal

VERSION = 'category-v1'
PREFIX = 'Correct these validation failures using only the approved context: '


def feedback_version(style):
    return VERSION if style == 'actionable' else style + '-v1'


def category(error):
    code = error.get('code', '')
    if code == 'JSON_INVALID':
        return 'invalid_json'
    if code in {'CONTEXT_MISMATCH', 'STATE_MISMATCH'}:
        return 'source_value'
    if code in {'RELATION_MISMATCH', 'RELATION_TYPE_INVALID', 'CALCULATION_INPUT_INVALID'}:
        return 'relationship'
    if code in {'SCHEMA_INVALID', 'CANDIDATE_SCHEMA_INVALID'}:
        return 'schema'
    return 'output'


def _short(text, limit=240):
    return text if len(text) <= limit else text[:limit] + '…'


def _value(value):
    """An omitted value is explicitly a summary, never a truncated replacement."""
    if len(canonical(value)) <= 160:
        return value
    return {'omitted': True, 'type': type(value).__name__,
            'hint': 'Use the original approved context or declared rule.'}


def _difference(actual, expected, tokens=()):
    """First differing JSON path, with absence distinct from a literal null."""
    if isinstance(actual, dict) and isinstance(expected, dict):
        for key in sorted(actual.keys() | expected.keys()):
            path = (*tokens, key)
            if key not in actual:
                return path, {'actualMissing': True, 'expected': _value(expected[key])}
            if key not in expected:
                return path, {'actual': _value(actual[key]), 'expectedMissing': True}
            found = _difference(actual[key], expected[key], path)
            if found:
                return found
        return None
    if isinstance(actual, list) and isinstance(expected, list):
        for index, (left, right) in enumerate(zip(actual, expected)):
            found = _difference(left, right, (*tokens, index))
            if found:
                return found
        index = min(len(actual), len(expected))
        if len(actual) < len(expected):
            return (*tokens, index), {'actualMissing': True, 'expected': _value(expected[index])}
        if len(actual) > len(expected):
            return (*tokens, index), {'actual': _value(actual[index]), 'expectedMissing': True}
        return None
    return None if json_equal(actual, expected) else (tokens, {'actual': _value(actual), 'expected': _value(expected)})


def source_error(error, document, bindings):
    """Attach one approved binding mismatch; retain the complete validator error.

    Locations here are relative to the contract document (tool arguments for an
    envelope), just like the effective-schema diagnostics. Only active bindings
    supplied by effective_schema are eligible; unapproved context is never read.
    """
    result = {**error, 'code': 'CONTEXT_MISMATCH', 'stage': 'context'}
    location = parts(error.get('instanceLocation', ''))
    for binding in sorted(bindings, key=lambda b: len(parts(b['instanceLocation'])), reverse=True):
        target = parts(binding['instanceLocation'])
        if target[:len(location)] != location and location[:len(target)] != target:
            continue
        keyword = binding.get('keyword', 'const')
        try:
            actual = resolve(document, binding['instanceLocation'])
        except KeyError:
            suffix, detail = (), {'actualMissing': True}
            if keyword == 'const':
                detail['expected'] = _value(binding['value'])
        else:
            if keyword == 'const':
                difference = _difference(actual, binding['value'])
                if difference is None:
                    continue
                suffix, detail = difference
            else:
                # Bounds/enum are constraints, not replacement field values.
                if Draft202012Validator({keyword: binding['value']}).is_valid(actual):
                    continue
                suffix, detail = (), {'actual': _value(actual), 'constraint': _value(binding['value'])}
        result['sourceMismatch'] = {
            'instanceLocation': pointer([*target, *suffix]),
            'contextLocation': pointer([*parts(binding['contextLocation']), *suffix]),
            'keyword': keyword, **detail,
        }
        break
    return result


RELATION_HINTS = {
    'product_equals': 'Recompute the target as the product of the declared operands.',
    'sum_equals': 'Recompute the target as the sum of the declared operands.',
    'count_equals': 'Set the target to the number of items in the declared array.',
    'sum_items_equals': 'Sum the declared item field in the array into the target.',
    'date_before': 'The left date must be strictly before the right date, using YYYY-MM-DD.',
    'equals': 'The declared left and right values must agree.',
    'reference_member': 'Select a value from the declared approved context array.',
    'member_of': 'Select a value present in the declared document array.',
    'unique_by': 'Remove duplicate keys at the declared item pointer without changing approved values.',
}


def actionable_entry(error):
    group = category(error)
    entry = {'category': group, **{k: error[k] for k in (
        'code', 'stage', 'instanceLocation', 'schemaLocation', 'keyword', 'ruleId', 'kind',
        'inputLocations', 'protectedInputs', 'jsonError') if k in error}}
    if group == 'invalid_json':
        hint = error.get('repairHint', 'Return one complete JSON value; fix the reported JSON error and preserve approved field values.')
        entry['message'] = _short(error.get('message', 'Invalid JSON.'))
    elif group == 'source_value':
        hint = 'Correct the bound field from approved context; preserve other approved values. Recheck the entire binding after this first mismatch.'
        entry['message'] = 'The output violates an approved source binding.'
        if 'sourceMismatch' in error:
            entry['sourceMismatch'] = error['sourceMismatch']
        # Legacy confirmed-state diagnostics carry an explicit field/value pair.
        if 'field' in error:
            entry['instanceLocation'] = pointer(['arguments', error['field']])
        for key in ('actual', 'expected'):
            if key in error:
                entry[key] = _value(error[key])
    elif group == 'relationship':
        hint = RELATION_HINTS.get(error.get('kind'), 'Correct the declared relationship using its input locations.')
        if error.get('code') in {'RELATION_TYPE_INVALID', 'CALCULATION_INPUT_INVALID'}:
            hint = 'Correct the type or format of the declared rule inputs. ' + hint
        if error.get('code') == 'CALCULATION_INPUT_INVALID':
            hint = 'Correct the declared calculation inputs; keep application-computed targets omitted.'
        hint += ' Preserve all approved inputs; do not alter them to make a rule pass.'
        entry['message'] = _short(error.get('message', 'Relationship validation failed.'))
        for key in ('actual', 'expected'):
            if key in error:
                entry[key] = _value(error[key])
    elif group == 'schema':
        hint = 'Correct the field against the output schema; preserve approved source values.'
        entry['message'] = _short(error.get('message', 'Output schema validation failed.'))
        if error.get('details'):
            entry['branches'] = [{k: _short(e[k]) if k == 'message' else e[k]
                                  for k in ('instanceLocation', 'schemaLocation', 'keyword', 'message') if k in e}
                                 for e in error['details'][:3]]
    else:
        hint = 'Return the complete JSON output required by the contract.'
        entry['message'] = _short(error.get('message', 'No final output.'))
    entry['repairHint'] = hint
    return entry


def actionable_message(errors, max_chars):
    """Pack whole entries, never slice JSON or let one large error hide later ones."""
    if max_chars < 128:
        raise ValueError('Repair feedback requires at least 128 characters')
    entries = []
    for error in errors:
        entry = actionable_entry(error)
        variants = [entry,
                    {k: v for k, v in entry.items() if k not in {'branches', 'message', 'actual', 'expected'}},
                    {k: entry[k] for k in ('category', 'code', 'instanceLocation', 'ruleId', 'kind', 'sourceMismatch', 'repairHint') if k in entry},
                    {k: entry[k] for k in ('category', 'code', 'instanceLocation') if k in entry},
                    {k: entry[k] for k in ('category', 'code') if k in entry},
                    {'category': entry['category']}]
        for candidate in variants:
            if len(PREFIX + canonical([*entries, candidate])) <= max_chars:
                entries.append(candidate)
                break
    return PREFIX + canonical(entries)
