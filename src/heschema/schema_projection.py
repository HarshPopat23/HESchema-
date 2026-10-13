"""Conservative provider projections with explicit preconditions and semantic manifests."""

import copy
import re

from .diagnostics import pointer, resolve
from .jsonio import canonical, digest
from .schema import check_schema, schema_children

VERSION = '1'
OBJECT_KEYS = {'type', 'properties', 'required', 'additionalProperties', 'title', 'description', '$schema', '$defs'}


def _merge_objects(shared, branch):
    if not isinstance(branch, dict) or set(branch) - OBJECT_KEYS or branch.get('type', 'object') != 'object':
        raise ValueError('Branch must contain only supported object constraints')
    a, b = shared.get('properties', {}), branch.get('properties', {})
    # A closed shared object must already admit every branch property (and conversely).
    if shared.get('additionalProperties') is False and set(b) - set(a):
        raise ValueError('Closed shared object excludes a branch property')
    if branch.get('additionalProperties') is False and set(a) - set(b):
        raise ValueError('Closed branch excludes a shared property')
    if any(x.get('additionalProperties', True) not in (True, False) for x in (shared, branch)):
        raise ValueError('Schema-valued additionalProperties requires separate reasoning')
    properties = copy.deepcopy(a)
    for key, value in b.items():
        properties[key] = {'allOf': [properties[key], copy.deepcopy(value)]} if key in properties and properties[key] != value else copy.deepcopy(value)
    result = {'type': 'object', 'properties': properties,
              'required': sorted(set(shared.get('required', [])) | set(branch.get('required', [])))}
    if shared.get('additionalProperties') is False or branch.get('additionalProperties') is False:
        result['additionalProperties'] = False
    return result


def project_schema(original, effective=None):
    check_schema(original)
    effective = copy.deepcopy(original if effective is None else effective)
    check_schema(effective)
    root, applied, rejected, locations = copy.deepcopy(effective), [], [], []
    nodes = list(_nodes(root))
    sensitive = {'$id', '$anchor', '$dynamicAnchor', '$dynamicRef', 'unevaluatedProperties', 'unevaluatedItems'}
    has_sensitive = any(set(n) & sensitive for _, n in nodes if isinstance(n, dict))

    def record(rule, path, preconditions):
        applied.append({'rule': rule, 'version': VERSION, 'preconditions': preconditions, 'equivalence': 'equivalent_for_declared_subset'})
        locations.append({'original': pointer(path), 'generated': pointer(path), 'mapping': 'transformed_subtree'})

    # Bundle only acyclic local $defs references with no URI scopes or annotation-sensitive unevaluated checks.
    def bundle(node, path=(), stack=()):
        if isinstance(node, bool):
            return node
        result = copy.deepcopy(node)
        ref = result.get('$ref')
        if ref is not None:
            if ref in stack:
                raise ValueError('Recursive reference')
            if has_sensitive or not ref.startswith('#/$defs/') or ref in stack:
                rejected.append({'location': pointer(path), 'rule': 'bundle_local_defs', 'reason': 'Requires acyclic local $defs pointers without scopes or unevaluated keywords'})
            else:
                target = resolve(root, ref[1:])
                if not isinstance(target, (dict, bool)):
                    raise ValueError('Reference target must be a schema')
                target = bundle(target, path, (*stack, ref))
                siblings = {k: v for k, v in result.items() if k != '$ref'}
                result = {'allOf': [target, bundle(siblings, path, stack)]} if siblings else target
                record('bundle_local_defs', path, ['local $defs pointer', 'acyclic', 'no URI scopes or unevaluated keywords'])
                return result
        if isinstance(result, dict):
            for tokens, child in list(schema_children(result)):
                parent = result
                for token in tokens[:-1]:
                    parent = parent[token]
                parent[tokens[-1]] = bundle(child, (*path, *tokens), stack)
        return result

    # Avoid visiting references twice after replacement; recursive schemas remain unchanged.
    if not has_sensitive and any('$ref' in n for _, n in nodes if isinstance(n, dict)):
        try:
            root = bundle(root)
        except (KeyError, ValueError, RecursionError):
            root = copy.deepcopy(effective)
            applied.clear()
            locations.clear()
            rejected.append({'location': '', 'rule': 'bundle_local_defs', 'reason': 'Unresolvable or recursive reference'})

    def transform(node, path=()):
        if not isinstance(node, dict):
            return node
        node = copy.deepcopy(node)
        # Finite conditional expansion is deliberately restricted to required string tags.
        if 'if' in node and not has_sensitive:
            try:
                condition = node['if']
                if set(condition) != {'properties', 'required'} or len(condition['properties']) != 1:
                    raise ValueError('Condition must require exactly one constant tag')
                tag, test = next(iter(condition['properties'].items()))
                if condition['required'] != [tag] or set(test) != {'const'} or not isinstance(test['const'], str):
                    raise ValueError('Condition must require one string constant')
                base = {k: v for k, v in node.items() if k not in {'if', 'then', 'else'}}
                if set(base) - OBJECT_KEYS or base.get('type') != 'object' or tag not in base.get('required', []):
                    raise ValueError('Required object tag and simple shared object constraints needed')
                tags = base['properties'][tag].get('enum')
                if not isinstance(tags, list) or not 1 <= len(tags) <= 16 or any(not isinstance(t, str) for t in tags) or len(set(tags)) != len(tags):
                    raise ValueError('Tag must have a distinct finite string enum')
                branches = []
                for value in tags:
                    branch = _merge_objects(base, node.get('then' if value == test['const'] else 'else', {}))
                    branch['properties'][tag] = {'allOf': [branch['properties'][tag], {'const': value}]}
                    branches.append(branch)
                node = {k: copy.deepcopy(v) for k, v in base.items() if k in {'$schema', '$defs', 'title', 'description'}} | {'oneOf': branches}
                record('finite_required_tag_conditional', path, ['required string tag', 'finite enum <=16', 'compatible simple objects', 'disjoint tag branches'])
            except (ValueError, KeyError, TypeError) as exc:
                rejected.append({'location': pointer(path), 'rule': 'finite_required_tag_conditional', 'reason': str(exc)})
        if 'oneOf' in node and 'properties' in node and not has_sensitive:
            try:
                shared = {k: v for k, v in node.items() if k != 'oneOf'}
                if set(shared) - OBJECT_KEYS or shared.get('type') != 'object':
                    raise ValueError('Simple shared object required')
                branches = [_merge_objects(shared, b) for b in node['oneOf']]
                tags = []
                for b in node['oneOf']:
                    tags.append({k: v['const'] for k, v in b.get('properties', {}).items() if isinstance(v, dict) and set(v) == {'const'} and isinstance(v['const'], str) and k in set(b.get('required', [])) | set(shared.get('required', []))})
                disjoint = any(all(key in tags[i] for i in range(len(tags))) and len({t[key] for t in tags}) == len(tags) for key in (tags[0] if tags else {}))
                if not disjoint:
                    raise ValueError('oneOf branches need pairwise distinct required string tags')
                node = {k: v for k, v in shared.items() if k in {'$schema', '$defs', 'title', 'description'}} | {'oneOf': branches}
                record('flatten_shared_tagged_object', path, ['compatible simple objects', 'distinct required string constants'])
            except (ValueError, TypeError) as exc:
                rejected.append({'location': pointer(path), 'rule': 'flatten_shared_tagged_object', 'reason': str(exc)})
        if isinstance(node.get('pattern'), str):
            pattern = re.sub(r'(?<!\\)\\/', '/', node['pattern'])
            if pattern != node['pattern']:
                node['pattern'] = pattern
                record('literal_slash_escape', path, ['escaped literal slash', 'unchanged Python/ECMA literal semantics'])
        for tokens, child in list(schema_children(node)):
            parent = node
            for token in tokens[:-1]:
                parent = parent[token]
            parent[tokens[-1]] = transform(child, (*path, *tokens))
        return node

    generated = transform(root)
    check_schema(generated)
    residuals = [{'location': pointer(path), 'keywords': sorted(set(node) & {'if', 'then', 'else', '$ref', '$dynamicRef', 'uniqueItems', 'allOf', 'oneOf'})}
                 for path, node in _nodes(generated) if isinstance(node, dict) and set(node) & {'if', 'then', 'else', '$ref', '$dynamicRef', 'uniqueItems', 'allOf', 'oneOf'}]
    manifest = {'manifestVersion': VERSION, 'originalHash': digest(original), 'effectiveHash': digest(effective),
                'generatedHash': digest(generated), 'transforms': applied, 'notApplied': rejected,
                'equivalence': 'equivalent_for_declared_subset' if applied else 'identity',
                'unsupportedResiduals': residuals, 'locationMap': locations,
                'equivalenceScope': 'validation outcomes; annotation collections are not guaranteed equivalent',
                'notice': 'Residual keywords have unknown provider enforcement. Differential tests are not a general equivalence proof.'}
    # Canonical serialization is used for identity only, not to infer semantic equivalence.
    assert canonical(original)  # Accept both true and false schemas.
    return generated, manifest


def _nodes(schema, path=()):
    yield path, schema
    if isinstance(schema, dict):
        for tokens, child in schema_children(schema):
            yield from _nodes(child, (*path, *tokens))
