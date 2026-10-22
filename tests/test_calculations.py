import copy
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from heschema.api import create_app
from heschema.calculations import (
    calculation_input_schema,
    calculation_plan,
    validate_with_calculations,
)
from heschema.contracts import Contract
from heschema.jsonio import canonical, loads
from heschema.providers import ROOT as PROJECT_ROOT
from heschema.providers import Generation
from heschema.registry import ContractRegistry
from heschema.rules import calculation_value, evaluate_rules
from heschema.schema import SchemaEngine
from heschema.state import StateStore
from heschema.validation import envelope, validate_contract

SCHEMA = {'type': 'object', 'properties': {
    'items': {'type': 'array', 'items': {'type': 'object', 'properties': {
        'amountMinor': {'type': 'integer'}}, 'required': ['amountMinor'], 'additionalProperties': False}},
    'count': {'type': 'integer', 'minimum': 0}, 'totalMinor': {'type': 'integer'},
}, 'required': ['items', 'count', 'totalMinor'], 'additionalProperties': False}
RULES = [
    {'id': 'count', 'kind': 'count_equals', 'arrayLocation': '/items', 'target': '/count'},
    {'id': 'sum', 'kind': 'sum_items_equals', 'arrayLocation': '/items',
     'itemLocation': '/amountMinor', 'target': '/totalMinor'},
]
INPUT = {'items': [{'amountMinor': 1250}, {'amountMinor': 99}]}
FULL = {**INPUT, 'count': 2, 'totalMinor': 1349}


def contract(*, compute=True, schema=None, output_kind='document'):
    rules = copy.deepcopy(RULES)
    if compute:
        rules = [{**rule, 'compute': 'application'} for rule in rules]
    return Contract('inventory-calc', '1', copy.deepcopy(schema or SCHEMA), output_kind,
                    'prepare_inventory' if output_kind == 'tool_envelope' else None,
                    bindings=[{'instanceLocation': '/items', 'contextLocation': '/items'}],
                    relationships=rules)


def snapshot():
    return {'id': 'source', 'version': 1, 'confirmed': True, 'data': copy.deepcopy(INPUT),
            'approvedPointers': ['/items'], 'facts': []}


@pytest.fixture
def engine():
    value = SchemaEngine()
    yield value
    value.close()


def test_default_and_explicit_model_do_not_calculate_or_change_validation(engine):
    c = contract(compute=False)
    before = copy.deepcopy(c.as_dict())
    assert calculation_plan(c) == []
    assert not validate_with_calculations(INPUT, engine, c, snapshot())['accepted']
    wrong = {**FULL, 'totalMinor': 25}
    assert not validate_with_calculations(wrong, engine, c, snapshot())['accepted']
    for rules in [c.relationships, [{**r, 'compute': 'model'} for r in c.relationships]]:
        result = validate_with_calculations(FULL, engine, replace(c, relationships=rules), snapshot())
        assert result['success'] and 'calculation' not in result
    assert c.as_dict() == before


@pytest.mark.parametrize('items,total', [([], 0), ([{'amountMinor': 10**100}, {'amountMinor': -1}], 10**100 - 1)])
def test_counts_sums_empty_arrays_large_integers_and_no_mutation(engine, items, total):
    c = contract()
    raw = {'items': items}
    snap = {**snapshot(), 'data': raw}
    before = copy.deepcopy((raw, snap, c.as_dict()))
    result = validate_with_calculations(raw, engine, c, snap)
    assert result['success']
    assert result['parsed'] == {'items': items, 'count': len(items), 'totalMinor': total}
    assert result['calculation']['status'] == 'applied'
    assert result['calculation']['sourceValid'] is True
    assert result['calculation']['correctnessScope'] == 'assembled_system_output'
    assert (raw, snap, c.as_dict()) == before


@pytest.mark.parametrize('kind,expected', [('sum_equals', 16), ('product_equals', 63)])
def test_scalar_calculations_share_exact_arithmetic_with_relationship_checks(engine, kind, expected):
    c = Contract('scalar', '1', {'type': 'object', 'properties': {
        'a': {'type': 'integer'}, 'b': {'type': 'integer'}, 'total': {'type': 'integer'}},
        'required': ['a', 'b', 'total'], 'additionalProperties': False},
        relationships=[{'id': 'total', 'kind': kind, 'operands': ['/a', '/b'],
                        'target': '/total', 'compute': 'application'}])
    result = validate_with_calculations({'a': 7, 'b': 9}, engine, c)
    assert result['accepted'] and not result['success']  # No approved intent was declared.
    assert result['calculation']['sourceValid'] is None
    assert result['parsed']['total'] == expected
    assert validate_contract(result['parsed'], engine, c)['relationships']['status'] == 'valid'


@pytest.mark.parametrize('value', [True, 1.5, 1e25])
def test_invalid_numeric_operands_cannot_be_converted_or_rounded(engine, value):
    schema = copy.deepcopy(SCHEMA)
    schema['properties']['items']['items']['properties']['amountMinor'] = True
    c = contract(schema=schema)
    raw = {'items': [{'amountMinor': value}]}
    result = validate_with_calculations(raw, engine, c, {**snapshot(), 'data': raw})
    assert not result['accepted'] and result['calculation']['values'] == []
    assert result['errors'][0]['code'] == 'CALCULATION_INPUT_INVALID'
    assert 'count' not in raw  # The successful first calculation was not partially applied.


@pytest.mark.parametrize('raw', [
    {'items': [{'amountMinor': 100}]},  # Changed source facts.
    {'items': 'wrong type'},
    {**INPUT, 'count': 2},  # Do not silently overwrite a model-supplied computed field.
    FULL,  # Even a correct complete document is not the declared generation-input shape.
    {**INPUT, 'extra': 1},
])
def test_inputs_and_approved_sources_are_checked_before_calculation(engine, monkeypatch, raw):
    def forbidden(*args):
        raise AssertionError('Calculation must not run on invalid or unapproved inputs')
    monkeypatch.setattr('heschema.calculations.calculation_value', forbidden)
    result = validate_with_calculations(raw, engine, contract(), snapshot())
    assert not result['accepted'] and result['calculation']['status'] == 'blocked'
    assert result['calculation']['values'] == []


def test_default_arithmetic_diagnostics_preserve_missing_evidence_precedence():
    rules = [{'id': 'sum', 'kind': 'sum_equals', 'operands': ['/a'], 'target': '/total'}]
    assert evaluate_rules({'a': True}, rules)['status'] == 'needs_context'
    assert evaluate_rules({'items': [{'amountMinor': True}]}, [RULES[1]])['status'] == 'needs_context'


def test_documented_example_is_executable_and_separates_raw_from_system_output(engine):
    example = loads((PROJECT_ROOT / 'examples/contracts/application-calculations.json').read_text(encoding='utf-8'))
    c = Contract(**example['contract'])
    snap = {'id': 'example', 'version': 1, 'confirmed': True, 'facts': [], **example['context']}
    result = validate_with_calculations(example['modelOutput'], engine, c, snap)
    assert result['success'] and result['parsed'] == example['expectedOutput']
    assert result['calculation']['pipelineMs'] >= result['validationMs']
    assert not validate_contract(example['modelOutput'], engine, c, snap)['accepted']


def test_missing_approval_and_final_target_constraints_fail_closed(engine):
    assert validate_with_calculations(INPUT, engine, contract())['result'] == 'NEEDS_CONTEXT'
    schema = copy.deepcopy(SCHEMA)
    schema['properties']['totalMinor']['maximum'] = 100
    result = validate_with_calculations(INPUT, engine, contract(schema=schema), snapshot())
    assert result['calculation']['status'] == 'applied'
    assert result['parsed']['totalMinor'] == 1349
    assert not result['accepted'] and result['stages']['originalSchema'] == 'invalid'


def test_only_selected_relationships_are_calculated_and_other_rules_still_fail(engine):
    c = contract(compute=False)
    c = replace(c, relationships=[{**c.relationships[0], 'compute': 'application'}, c.relationships[1]])
    result = validate_with_calculations({**INPUT, 'totalMinor': 25}, engine, c, snapshot())
    assert not result['accepted'] and result['stages']['relationships'] == 'invalid'
    assert result['parsed'] == {**INPUT, 'totalMinor': 25, 'count': 2}
    assert result['calculation']['ruleIds'] == ['count']
    # /contracts/validate remains a checker, not a mutation endpoint.
    assert not validate_contract(INPUT, engine, c, snapshot())['accepted']


@pytest.mark.parametrize('raw', ['not JSON', '{"items":[],"items":[]}', '<think>x</think>{"items":[]}'])
def test_invalid_raw_output_is_never_salvaged(engine, raw):
    result = validate_with_calculations(raw, engine, contract(), snapshot())
    assert result['stages']['json'] == 'invalid' and not result['accepted']
    assert result['calculation']['status'] == 'blocked'


def test_truncated_output_is_not_calculated(engine):
    raw = canonical(INPUT)
    result = validate_with_calculations(raw, engine, contract(), snapshot(),
                                         generation=Generation(raw, metadata={'finish_reason': 'length'}))
    assert not result['accepted'] and result['calculation']['values'] == []


def test_escaped_targets_and_original_constraints_survive_schema_reduction(engine):
    schema = {'type': 'object', 'properties': {
        'items': {'type': 'array', 'items': {'type': 'integer'}, 'minItems': 1},
        'n/~': {'type': 'integer', 'minimum': 1}, 'fixed': {'const': 'keep-me'}},
        'required': ['items', 'n/~', 'fixed'], 'additionalProperties': False}
    c = Contract('escaped', '1', schema, relationships=[{
        'id': 'n', 'kind': 'count_equals', 'arrayLocation': '/items',
        'target': '/n~1~0', 'compute': 'application'}])
    reduced = calculation_input_schema(schema, calculation_plan(c))
    assert reduced['properties']['fixed'] == {'const': 'keep-me'}
    assert reduced['properties']['items']['minItems'] == 1
    result = validate_with_calculations({'items': [1], 'fixed': 'keep-me'}, engine, c)
    assert result['accepted'] and result['parsed']['n/~'] == 1
    assert not validate_with_calculations({'items': [], 'fixed': 'keep-me'}, engine, c)['accepted']


@pytest.mark.parametrize('change', [
    'bad_compute', 'non_arithmetic', 'duplicate_target', 'self_reference', 'dependent',
    'nested_target', 'missing_target', 'noninteger_target', 'open_schema', 'root_conditional',
    'root_count', 'reference', 'bound_target', 'root_binding',
])
def test_unsupported_or_ambiguous_plans_are_rejected_at_registration(change):
    data = contract().as_dict()
    if change == 'bad_compute':
        data['relationships'][0]['compute'] = True
    elif change == 'non_arithmetic':
        data['relationships'] = [{'id': 'e', 'kind': 'equals', 'left': '/count',
                                  'right': '/totalMinor', 'compute': 'application'}]
    elif change == 'duplicate_target':
        data['relationships'][1]['target'] = '/count'
    elif change == 'self_reference':
        data['relationships'][0]['arrayLocation'] = '/count'
    elif change == 'dependent':
        data['relationships'][1] = {'id': 's', 'kind': 'sum_equals', 'target': '/totalMinor',
                                   'operands': ['/count'], 'compute': 'application'}
    elif change == 'nested_target':
        data['relationships'][0]['target'] = '/nested/count'
    elif change == 'missing_target':
        data['relationships'][0]['target'] = '/missing'
    elif change == 'noninteger_target':
        data['schema']['properties']['count'] = {'type': 'number'}
    elif change == 'open_schema':
        data['schema']['additionalProperties'] = True
    elif change == 'root_conditional':
        data['schema']['allOf'] = [{}]
    elif change == 'root_count':
        data['schema']['minProperties'] = 3
    elif change == 'reference':
        data['schema']['properties']['totalMinor']['$ref'] = '#/properties/count'
    elif change == 'bound_target':
        data['bindings'].append({'instanceLocation': '/count', 'contextLocation': '/count'})
    elif change == 'root_binding':
        data['bindings'].append({'instanceLocation': '', 'contextLocation': ''})
    with pytest.raises(ValueError):
        ContractRegistry().register(data)


def test_selected_relationships_persist_and_immutable_versions_require_new_definition(tmp_path):
    path = tmp_path / 'registry.sqlite'
    before = contract(compute=False)
    registry = ContractRegistry(path)
    registry.register(before)
    with pytest.raises(ValueError, match='immutable'):
        registry.register(contract())
    registry.register(replace(contract(), version='2'))
    reloaded = ContractRegistry(path)
    assert calculation_plan(reloaded.get('inventory-calc', '1')) == []
    assert len(calculation_plan(reloaded.get('inventory-calc', '2'))) == 2


def setup_api(client, c):
    registration = client.post('/contracts', json=c.as_dict())
    assert registration.status_code == 201, registration.text
    response = client.post('/contexts', json={
        'contractId': c.id, 'contractVersion': c.version,
        'data': INPUT, 'approvedPointers': ['/items']})
    assert response.status_code == 201, response.text
    ctx = response.json()
    assert client.post(f"/contexts/{ctx['id']}/confirm", json={'version': 1}).status_code == 200
    return {'contractId': c.id, 'contractVersion': c.version, 'contextId': ctx['id'],
            'contextVersion': 1, 'prompt': 'Prepare inventory', 'provider': 'mock'}


@pytest.mark.parametrize('mode', ['prompt_only', 'native_original', 'native_projected'])
@pytest.mark.parametrize('style', ['full', 'compact'])
@pytest.mark.parametrize('output_kind', ['document', 'tool_envelope'])
def test_api_generation_preserves_raw_model_evidence_and_validates_assembled_output(
        tmp_path, monkeypatch, mode, style, output_kind):
    monkeypatch.delenv('HESCHEMA_API_TOKEN', raising=False)
    c = contract(output_kind=output_kind)
    raw = INPUT if output_kind == 'document' else envelope('call_tool', c.tool, INPUT)
    seen = []
    async def fake(self, messages, *args, **kwargs):
        seen.append((copy.deepcopy(messages), kwargs))
        return Generation(canonical(raw), input_tokens=100, output_tokens=25,
                          metadata={'finish_reason': 'stop'})
    monkeypatch.setattr('heschema.providers.Provider.generate', fake)
    with TestClient(create_app(tmp_path / 'state.sqlite')) as client:
        body = setup_api(client, c)
        response = client.post('/contracts/generate', json={**body, 'mode': mode, 'promptStyle': style})
        assert response.status_code == 200, response.text
        result = response.json()
        assert result['validation']['success']
        assert result['validation']['stages']['relationships'] == 'valid'
        assert not result['executionAuthorized']
        output = loads(result['output'])
        assert (output['arguments'] if output_kind == 'tool_envelope' else output) == FULL
        assert result['modelOutput'] == canonical(raw)
        attempt = result['repair']['attempts'][0]
        assert attempt['generation']['text'] == canonical(raw)
        assert attempt['generation']['output_tokens'] == 25
        assert attempt['evaluation']['parsed'] == output
        assert client.post('/contracts/validate', json={**body_without_generation(body),
                            'output': output}).json()['success']
        # Existing-output validation does not turn incomplete input into a correct answer.
        assert not client.post('/contracts/validate', json={**body_without_generation(body),
                               'output': raw}).json()['accepted']
    assert 'Application-computed fields: ["/count","/totalMinor"]' in seen[0][0][0]['content']
    if mode != 'prompt_only':
        generation_schema = seen[0][1]['format_schema']
        assert Draft202012Validator(generation_schema).is_valid(raw)
        assert not Draft202012Validator(generation_schema).is_valid(output)


def body_without_generation(body):
    return {key: value for key, value in body.items() if key not in {'prompt', 'provider'}}


def test_api_repairs_invalid_source_without_restarting_success_or_losing_raw_responses(tmp_path, monkeypatch):
    monkeypatch.delenv('HESCHEMA_API_TOKEN', raising=False)
    seen, calculations = [], []
    async def fake(self, messages, *args, **kwargs):
        seen.append(copy.deepcopy(messages))
        return Generation(canonical({'items': []} if len(seen) == 1 else INPUT),
                          metadata={'finish_reason': 'stop'})
    def calculate(document, rule):
        calculations.append(rule['id'])
        return calculation_value(document, rule)
    monkeypatch.setattr('heschema.providers.Provider.generate', fake)
    monkeypatch.setattr('heschema.calculations.calculation_value', calculate)
    with TestClient(create_app(tmp_path / 'state.sqlite')) as client:
        body = setup_api(client, contract())
        result = client.post('/contracts/generate', json={**body, 'repairs': 1}).json()
    assert result['validation']['success'] and result['repair']['requestsAttempted'] == 2
    assert result['repair']['firstEvaluation']['calculation']['status'] == 'blocked'
    assert calculations == ['count', 'sum']  # Invalid first inputs were never calculated.
    assert seen[1][-2]['content'] == '{"items":[]}'
    assert 'CONTEXT_MISMATCH' in seen[1][-1]['content']


@pytest.mark.parametrize('action', ['refuse', 'ask_clarification'])
def test_api_controls_skip_calculation_and_preserve_refusal(tmp_path, monkeypatch, action):
    monkeypatch.delenv('HESCHEMA_API_TOKEN', raising=False)
    raw = canonical(envelope(action, missing=['items'] if action == 'ask_clarification' else []))
    async def fake(self, *args, **kwargs):
        return Generation(raw, metadata={'finish_reason': 'stop'})
    monkeypatch.setattr('heschema.providers.Provider.generate', fake)
    with TestClient(create_app(tmp_path / 'state.sqlite')) as client:
        body = setup_api(client, contract(output_kind='tool_envelope'))
        result = client.post('/contracts/generate', json={**body, 'repairs': 2}).json()
    assert result['output'] == result['modelOutput'] == raw
    assert result['validation']['calculation']['status'] == 'not_applied'
    assert result['repair']['requestsAttempted'] == 1


def test_invalidation_while_generating_prevents_calculation_and_acceptance(tmp_path, monkeypatch):
    monkeypatch.delenv('HESCHEMA_API_TOKEN', raising=False)
    with TestClient(create_app(tmp_path / 'state.sqlite')) as client:
        body = setup_api(client, contract())
        async def fake(self, *args, **kwargs):
            StateStore(tmp_path / 'state.sqlite').invalidate_context(body['contextId'], 'local-operator', 1)
            return Generation(canonical(INPUT), metadata={'finish_reason': 'stop'})
        monkeypatch.setattr('heschema.providers.Provider.generate', fake)
        result = client.post('/contracts/generate', json={**body, 'repairs': 2}).json()
    assert result['repair']['stopReason'] == 'context_changed'
    assert not result['validation']['accepted']
    assert result['repair']['requestsAttempted'] == 1
    assert result['repair']['requestLedger'][0]['generation']['outputPresent']


def test_tolerance_calculation_rules():
    from heschema.rules import check_rules

    # check_rules rejects negative tolerance or non-numeric tolerance
    with pytest.raises(ValueError, match="tolerance"):
        check_rules([{"id": "r1", "kind": "sum_equals", "target": "/c", "operands": ["/a", "/b"], "tolerance": -0.01}])
    with pytest.raises(ValueError, match="tolerance"):
        check_rules([{"id": "r1", "kind": "sum_equals", "target": "/c", "operands": ["/a", "/b"], "tolerance": "tight"}])

    # sum_equals with tolerance
    rules = [{"id": "sum", "kind": "sum_equals", "target": "/total", "operands": ["/a", "/b"], "tolerance": 0.05}]
    check_rules(rules)

    # 10.0 + 20.0 = 30.0; actual = 30.04 (within 0.05 tolerance) -> valid
    doc_ok = {"a": 10.0, "b": 20.0, "total": 30.04}
    res_ok = evaluate_rules(doc_ok, rules)
    assert res_ok["status"] == "valid"

    # actual = 30.06 (exceeds 0.05 tolerance) -> invalid
    doc_fail = {"a": 10.0, "b": 20.0, "total": 30.06}
    res_fail = evaluate_rules(doc_fail, rules)
    assert res_fail["status"] == "invalid"

    # sum_items_equals with tolerance
    item_rules = [{"id": "item_sum", "kind": "sum_items_equals", "arrayLocation": "/items", "itemLocation": "/price", "target": "/total", "tolerance": 0.02}]
    check_rules(item_rules)
    assert evaluate_rules({"items": [{"price": 1.255}, {"price": 2.341}], "total": 3.60}, item_rules)["status"] == "valid"
    assert evaluate_rules({"items": [{"price": 1.255}, {"price": 2.341}], "total": 3.65}, item_rules)["status"] == "invalid"

