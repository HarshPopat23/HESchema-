import itertools

from heschema.capabilities import capability_profile, record_probe
from heschema.contracts import Contract, generation_envelope
from heschema.schema import SchemaEngine, check_schema
from heschema.schema_projection import project_schema


def equivalent_on(schema, witnesses):
    engine = SchemaEngine()
    generated, manifest = project_schema(schema)
    for value in witnesses:
        assert bool(engine.errors(schema, value)) == bool(engine.errors(generated, value)), value
    assert manifest['originalHash'] and manifest['generatedHash']
    return generated, manifest


def test_conditional_both_branches_missing_tag_extras_and_negative_prompts():
    schema = {'type': 'object', 'properties': {'kind': {'enum': ['a', 'b']}, 'x': {'type': 'integer'}}, 'required': ['kind'], 'additionalProperties': False,
              'if': {'properties': {'kind': {'const': 'a'}}, 'required': ['kind']}, 'then': {'properties': {'x': {'minimum': 2}}, 'required': ['x']}, 'else': {'properties': {'x': {'maximum': 1}}, 'required': ['x']}}
    values = [{'kind': k, 'x': x} for k, x in itertools.product(['a', 'b', 'c'], [-1, 0, 1, 2, 3, 'wrong', None])]
    values += [{}, {'x': 2}, {'kind': 'a'}, {'kind': 'b', 'x': 1, 'extra': True}, None, 1]
    generated, manifest = equivalent_on(schema, values)
    assert 'if' not in generated and manifest['transforms'][0]['rule'] == 'finite_required_tag_conditional'
    # Missing discriminator in the authoring contract cannot be silently strengthened.
    loose = {**schema, 'required': [], 'if': {'properties': {'kind': {'const': 'a'}}}}
    generated, manifest = equivalent_on(loose, values)
    assert 'if' in generated and manifest['notApplied']


def test_shared_tagged_alternatives_and_overlapping_unions_preserve_oneof():
    schema = {'type': 'object', 'properties': {'kind': {'type': 'string'}, 'x': {'type': 'integer'}}, 'required': ['kind', 'x'], 'additionalProperties': False,
              'oneOf': [{'properties': {'kind': {'const': 'a'}, 'x': {'minimum': 1}}}, {'properties': {'kind': {'const': 'b'}, 'x': {'maximum': 1}}}]}
    generated, manifest = equivalent_on(schema, [{'kind': k, 'x': x} for k, x in itertools.product(['a', 'b', 'c'], [0, 1, 2])] + [{}, {'kind': 'a', 'x': 1, 'extra': 1}])
    assert 'properties' not in generated and manifest['transforms']
    overlapping = {'oneOf': [{'type': 'integer'}, {'minimum': 0}]}
    generated, _ = equivalent_on(overlapping, [-1, 0, 1, 'hello'])
    assert 'oneOf' in generated and 'anyOf' not in generated
    assert SchemaEngine().errors(generated, 1)  # A weakened anyOf would incorrectly accept this.


def test_uniqueness_is_retained_regex_is_conservative_and_data_not_schema():
    schema = {'type': 'array', 'items': {'type': 'string'}, 'uniqueItems': True}
    generated, _ = equivalent_on(schema, [[], ['a'], ['a', 'a'], ['a', 'b']])
    assert generated['uniqueItems']
    equivalent_on({'type': 'string', 'pattern': r'^a\/b$'}, ['a/b', 'aXb', 'a\\/b', 'a/bx'])
    digits, _ = project_schema({'type': 'string', 'pattern': r'^\d+$'})
    assert digits['pattern'] == r'^\d+$'  # No false ASCII/Unicode equivalence claim.
    data_schema = {'const': {'$ref': 'https://example.test/data'}}
    check_schema(data_schema)
    assert project_schema(data_schema)[0] == data_schema


def test_local_refs_recursive_refs_and_tool_envelope_reference_scopes():
    schema = {'type': 'object', '$defs': {'n': {'type': 'integer', 'minimum': 1}}, 'properties': {'x': {'$ref': '#/$defs/n'}}, 'required': ['x']}
    generated, _ = equivalent_on(schema, [{'x': 1}, {'x': 0}, {'x': 'bad'}, {}])
    assert '$ref' not in generated['properties']['x']
    recursive = {'$defs': {'tree': {'type': 'object', 'properties': {'child': {'$ref': '#/$defs/tree'}}}}, '$ref': '#/$defs/tree'}
    generated, _ = equivalent_on(recursive, [{}, {'child': {}}, {'child': 1}, 1])
    assert generated == recursive
    c = Contract('tool', '1', schema, 'tool_envelope', 'custom')
    envelope = generation_envelope(c, schema)
    engine = SchemaEngine()
    for action in ['call_tool', 'ask_clarification', 'refuse']:
        value = {'action': action, 'tool': 'custom' if action == 'call_tool' else None, 'arguments': {'x': 1} if action == 'call_tool' else {}, 'reason': '', 'missingFields': ['x'] if action == 'ask_clarification' else []}
        assert not engine.errors(envelope, value)
    assert engine.errors(envelope, {**value, 'arguments': {'x': 1}})


def test_capability_acceptance_does_not_establish_enforcement():
    p = capability_profile('ollama', 'native_original')
    p = record_probe(p, schema={}, request_accepted=True, original_valid=True, provenance='mock')
    assert p['keywordEnforcement'] == 'unknown'
    assert p['observations'][0]['outcome'] == 'observed_valid'
    assert capability_profile('openai', 'native_original')['adapterStatus'] == 'unsupported'
