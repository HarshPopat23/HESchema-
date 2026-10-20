"""Conjoin trusted constraints without mutating or weakening the original schema."""

import copy
import re
from datetime import datetime, timezone
from urllib.parse import quote

from jsonschema import Draft202012Validator, FormatChecker

from .diagnostics import parts, pointer, resolve
from .jsonio import digest
from .schema import schema_children


class ContextError(ValueError):
    pass


def trusted_information(snapshot):
    if not snapshot:
        return {}
    locations = set(snapshot.get('approvedPointers', [])) | {f['contextLocation'] for f in snapshot.get('facts', [])}
    return {location: copy.deepcopy(resolve(snapshot['data'], location)) for location in sorted(locations)}


def check_context(snapshot, *, version=None):
    if not snapshot or not snapshot.get('confirmed'):
        raise ContextError('Unconfirmed context')
    if version is not None and snapshot['version'] != version:
        raise ContextError('Stale context version')
    expires = snapshot.get('expiresAt')
    if expires and datetime.fromisoformat(expires) <= datetime.now(timezone.utc):
        raise ContextError('Context approval expired')
    for fact in snapshot.get('facts', []):
        if not fact.get('source') or not fact.get('version') or not fact.get('verified'):
            raise ContextError('External fact requires verified source/version evidence')
        if datetime.fromisoformat(fact['expiresAt']) <= datetime.now(timezone.utc):
            raise ContextError('External fact expired; confirm a new context version')
    return snapshot


def _array_index(token):
    if not re.fullmatch(r'0|[1-9][0-9]*', token):
        raise ContextError('Array binding requires a canonical numeric index')
    index = int(token)
    if index > 1024:
        raise ContextError('Array binding index exceeds the projection limit')
    return index


def _at_path(original, tokens, leaf):
    if not tokens:
        return copy.deepcopy(leaf)
    token, remaining = tokens[0], tokens[1:]
    node = original if isinstance(original, dict) else {}
    types = node.get('type')
    if types == 'array':
        index = _array_index(token)
        child = node.get('prefixItems', [])[index] if index < len(node.get('prefixItems', [])) else node.get('items', {})
        return {'type': 'array', 'minItems': index + 1,
                'prefixItems': [True] * index + [_at_path(child, remaining, leaf)]}
    if types != 'object':
        raise ContextError('Nested binding requires explicit object/array types on the original path')
    child = node.get('properties', {}).get(token, node.get('additionalProperties', {}))
    return {'type': 'object', 'required': [token], 'properties': {token: _at_path(child, remaining, leaf)}}


def _leaf(original, tokens):
    node = original
    location = []
    for token in tokens:
        if not isinstance(node, dict):
            return node, location
        if node.get('type') == 'array':
            idx = _array_index(token)
            path = ['prefixItems', idx] if idx < len(node.get('prefixItems', [])) else ['items']
            child = node['prefixItems'][idx] if path[0] == 'prefixItems' else node.get('items', {})
            present = path[0] in node
        else:
            present = token in node.get('properties', {}) or 'additionalProperties' in node
            path = ['properties', token] if token in node.get('properties', {}) else ['additionalProperties']
            child = node.get('properties', {}).get(token, node.get('additionalProperties', {}))
        location = [*location, *path] if location is not None and present else None
        node = child
    return node, location


def effective_schema(contract, snapshot=None):
    original = copy.deepcopy(contract.schema)
    active, missing, constraints = [], [], []
    data = snapshot['data'] if snapshot else {}
    approved = set(snapshot.get('approvedPointers', [])) if snapshot else set()
    approved |= {fact['contextLocation'] for fact in snapshot.get('facts', [])} if snapshot else set()
    if snapshot:
        check_context(snapshot)
        if snapshot.get('contractHash') and snapshot['contractHash'] != contract.identity['hash']:
            raise ContextError('Context belongs to a different contract/version')
        # Partial approval: validate only supplied values; required context fields can be absent.
        partial = copy.deepcopy(contract.contextSchema)
        def omit_required(node):
            if isinstance(node, dict):
                node.pop('required', None)
                for tokens, child in schema_children(node):
                    # Predicates/unions retain their own required discriminators;
                    # const/enum/default values are data, not subschemas.
                    if tokens[0] not in {'if', 'not', 'anyOf', 'oneOf', 'contains'}:
                        omit_required(child)
        omit_required(partial)
        errors = list(Draft202012Validator(partial, format_checker=FormatChecker()).iter_errors(data))
        if errors:
            raise ContextError('Context data violates its declared schema: ' + errors[0].message)
    original_validator = Draft202012Validator(original, format_checker=FormatChecker())
    for binding in contract.bindings:
        source = binding['contextLocation']
        try:
            if source not in approved:
                raise KeyError(source)
            value = copy.deepcopy(resolve(data, source))
        except KeyError:
            if binding.get('required', True):
                missing.append(binding['instanceLocation'])
            continue
        keyword = binding.get('keyword', 'const')
        if keyword == 'enum' and (not isinstance(value, list) or not value):
            raise ContextError('Trusted enum binding requires a nonempty array')
        if keyword in {'minimum', 'maximum'} and (type(value) not in {int, float}):
            raise ContextError('Trusted bounds require a number')
        tokens = parts(binding['instanceLocation'])
        leaf, location = _leaf(original, tokens)
        # Evaluate the field in its original resource, not as a detached schema.
        # A pointer lookup also preserves ancestor $id scopes for nested resources.
        field_schema = {'$ref': '#' + quote(pointer(location), safe='/~')} if location is not None else leaf
        validator = original_validator.evolve(schema=field_schema)
        if keyword == 'const' and not validator.is_valid(value):
            raise ContextError('Approved binding contradicts the original field schema')
        if keyword == 'enum' and not any(validator.is_valid(v) for v in value):
            raise ContextError('Trusted allowed set contradicts the original field schema')
        if isinstance(leaf, dict) and keyword == 'maximum' and leaf.get('minimum', value) > value:
            raise ContextError('Trusted maximum contradicts the original minimum')
        if isinstance(leaf, dict) and keyword == 'minimum' and leaf.get('maximum', value) < value:
            raise ContextError('Trusted minimum contradicts the original maximum')
        constraints.append(_at_path(original, tokens, {keyword: value}))
        active.append({**binding, 'value': value})
    # Keep local references anchored at the original root ($defs/$id are not moved).
    if constraints and isinstance(original, dict):
        schema = {**original, 'allOf': [*original.get('allOf', []), *constraints]}
    else:
        schema = {'allOf': [original, *constraints]} if constraints else original
    return schema, {'activeBindings': active, 'missingBindings': missing,
                    'hash': digest(snapshot) if snapshot else None,
                    'id': snapshot['id'] if snapshot else None,
                    'version': snapshot['version'] if snapshot else None}
