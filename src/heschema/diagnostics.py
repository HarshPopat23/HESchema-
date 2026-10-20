"""Stable diagnostic locations and runtime-only repair feedback."""

import re
from json import JSONDecodeError


def pointer(parts):
    return ''.join('/' + str(p).replace('~', '~0').replace('/', '~1') for p in parts)


def parts(location):
    if location == '':
        return []
    if not isinstance(location, str) or not location.startswith('/'):
        raise ValueError('Expected an RFC 6901 JSON Pointer')
    tokens = location[1:].split('/')
    if any(re.search(r'~(?![01])', t) for t in tokens):
        raise ValueError('Invalid JSON Pointer escape')
    return [t.replace('~1', '/').replace('~0', '~') for t in tokens]


def resolve(document, location):
    value = document
    for token in parts(location):
        if isinstance(value, list):
            if not re.fullmatch(r'0|[1-9][0-9]*', token):
                raise KeyError(location)
            try:
                value = value[int(token)]
            except IndexError:
                raise KeyError(location) from None
        elif isinstance(value, dict) and token in value:
            value = value[token]
        else:
            raise KeyError(location)
    return value


def diagnostic(code, stage, location='', message='', *, repair='correct_output', **details):
    return {'code': code, 'stage': stage, 'instanceLocation': location,
            'message': message, 'repair': repair, **details}


def json_parse_diagnostic(error):
    """Report syntax evidence without modifying text or guessing missing source values."""
    details = {}
    if isinstance(error, JSONDecodeError):
        trailing = error.msg == 'Extra data'
        details['jsonError'] = {
            'kind': 'trailing_content' if trailing else 'syntax', 'reason': error.msg,
            'offset': error.pos, 'line': error.lineno, 'column': error.colno,
        }
        details['repairHint'] = (
            'Return only the JSON value required by the output schema; remove trailing content '
            'after it and preserve approved field values.' if trailing else
            'Correct JSON syntax at the reported location; preserve approved field values '
            'and nested object/array boundaries.'
        )
    return diagnostic('JSON_INVALID', 'json', message=str(error), **details)


def schema_error(error, locations=None):
    location = pointer(error.absolute_path)
    evaluated = pointer(error.absolute_schema_path)
    source = (locations or {}).get(id(error.schema))
    keyword_location = source + pointer([error.validator]) if source is not None and error.validator is not None else evaluated
    result = diagnostic('SCHEMA_INVALID', 'schema', location, error.message,
                        schemaLocation=keyword_location, evaluationLocation=evaluated, keyword=error.validator)
    result['path'] = location  # Legacy alias; root is the empty pointer.
    if error.context:
        result['details'] = [schema_error(child, locations) for child in error.context]
    return result


def runtime_feedback(errors, *, allow_state=False):
    allowed = {'JSON_INVALID', 'SCHEMA_INVALID', 'CANDIDATE_SCHEMA_INVALID', 'RELATION_MISMATCH', 'RELATION_TYPE_INVALID',
               'CALCULATION_INPUT_INVALID'}
    if allow_state:
        allowed |= {'STATE_MISMATCH', 'CONTEXT_MISMATCH'}
    return [e for e in errors if e.get('code') in allowed and e.get('repair') != 'needs_context']
