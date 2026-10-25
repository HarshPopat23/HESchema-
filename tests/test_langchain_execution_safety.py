"""Observe actual tool side effects, not just returned diagnostics."""
import asyncio
import copy

import pytest

from heschema.guard import ContractViolationError
from heschema.integrations.langchain import HESchemaToolInterceptor, guard_tool


def contract(schema=None, relationships=None):
    return {'id': 'spy', 'version': '1', 'outputKind': 'document',
            'schema': schema or {'type': 'object', 'properties': {'x': {'type': 'integer', 'minimum': 1}},
                                 'required': ['x'], 'additionalProperties': False},
            'relationships': relationships or []}


class Spy:
    name = 'spy'

    def __init__(self):
        self.calls = []

    def invoke(self, data):
        self.calls.append(copy.deepcopy(data))
        return data

    run = invoke

    async def ainvoke(self, data):
        self.calls.append(copy.deepcopy(data))
        return data

    arun = ainvoke


def call(tool, method, data):
    result = getattr(tool, method)(data)
    return asyncio.run(result) if method.startswith('a') else result


@pytest.mark.parametrize('method', ['invoke', 'run', 'ainvoke', 'arun'])
@pytest.mark.parametrize('policy', ['repair', 'raise', 'refuse'])
@pytest.mark.parametrize('data', [{'x': 0}, {}, '{"x":0}', 'invalid json', [], None])
def test_rejected_inputs_never_execute(method, policy, data):
    tool = guard_tool(Spy(), contract(), on_fail=policy)
    if policy == 'refuse':
        assert call(tool, method, data)['action'] == 'refuse'
    else:
        with pytest.raises(ContractViolationError):
            call(tool, method, data)
    assert tool.calls == []


@pytest.mark.parametrize('policy', ['ignore', '', None])
def test_invalid_policy_does_not_wrap_or_invoke(policy):
    tool = Spy()
    with pytest.raises(ValueError):
        guard_tool(tool, contract(), on_fail=policy)
    assert tool.calls == []


@pytest.mark.parametrize('method', ['invoke', 'run', 'ainvoke', 'arun'])
def test_valid_input_executes_once(method):
    tool = guard_tool(Spy(), contract())
    assert call(tool, method, {'x': 1}) == {'x': 1}
    assert tool.calls == [{'x': 1}]


@pytest.mark.parametrize('parent', ['invoice', 'a/b~c'])
@pytest.mark.parametrize('method', ['invoke', 'run', 'ainvoke', 'arun'])
def test_nested_calculation_delivers_validated_document(parent, method):
    token = parent.replace('~', '~0').replace('/', '~1')
    schema = {'type': 'object', 'additionalProperties': False, 'required': [parent],
              'properties': {parent: {'type': 'object', 'additionalProperties': False,
                 'required': ['quantity', 'price', 'total'],
                 'properties': {k: {'type': 'integer', 'minimum': 1} for k in ['quantity', 'price', 'total']}}}}
    rules = [{'id': 'total', 'kind': 'product_equals', 'compute': 'application',
              'target': f'/{token}/total', 'operands': [f'/{token}/quantity', f'/{token}/price']}]
    spec = contract(schema, rules)
    tool = guard_tool(Spy(), spec)
    source = {parent: {'quantity': 2, 'price': 3}}
    expected = {parent: {'quantity': 2, 'price': 3, 'total': 6}}
    assert call(tool, method, source) == expected
    assert tool.calls == [expected]
    assert source == {parent: {'quantity': 2, 'price': 3}}
    assert HESchemaToolInterceptor({'spy': spec}).intercept('spy', expected) == expected
    invalid = {parent: {'quantity': 'wrong', 'price': 3}}
    with pytest.raises(ContractViolationError):
        call(tool, method, invalid)
    assert tool.calls == [expected]


@pytest.mark.parametrize('policy', ['repair', 'raise', 'refuse'])
def test_message_rejection_halts_instead_of_inserting_refusal_arguments(policy):
    middleware = HESchemaToolInterceptor({'spy': contract()}, on_fail=policy)
    message = {'tool_calls': [{'name': 'spy', 'args': {}}]}
    with pytest.raises(ContractViolationError):
        middleware.intercept_message(message)
    assert message['tool_calls'][0]['args'] == {}

@pytest.mark.parametrize('action', ['refuse', 'ask_clarification'])
def test_control_envelope_does_not_execute(action):
    spec = {**contract(), 'outputKind': 'tool_envelope', 'tool': 'spy'}
    tool = guard_tool(Spy(), spec)
    envelope = {'action': action, 'tool': None, 'arguments': {},
                'missingFields': ['x'] if action == 'ask_clarification' else [], 'reason': 'need input'}
    with pytest.raises(ContractViolationError):
        tool.invoke(envelope)
    assert tool.calls == []


def test_call_envelope_delivers_arguments_only():
    tool = guard_tool(Spy(), {**contract(), 'outputKind': 'tool_envelope', 'tool': 'spy'})
    assert tool.invoke({'action': 'call_tool', 'tool': 'spy', 'arguments': {'x': 1},
                        'missingFields': [], 'reason': 'ready'}) == {'x': 1}
    assert tool.calls == [{'x': 1}]

@pytest.mark.parametrize('method', ['invoke', 'run', 'ainvoke', 'arun'])
def test_keyword_input_is_guarded_without_changing_signature(method):
    tool = guard_tool(Spy(), contract())
    result = getattr(tool, method)(data={'x': 1})
    assert (asyncio.run(result) if method.startswith('a') else result) == {'x': 1}
    with pytest.raises(ContractViolationError):
        result = getattr(tool, method)(data={'x': 0})
        if method.startswith('a'):
            asyncio.run(result)
    assert tool.calls == [{'x': 1}]


def test_unsupported_array_calculation_is_rejected_before_wrapping():
    schema = {'type': 'object', 'additionalProperties': False, 'required': ['items'],
              'properties': {'items': {'type': 'array', 'items': {'type': 'integer'}}}}
    rules = [{'id': 'bad', 'kind': 'sum_equals', 'compute': 'application',
              'target': '/items/0', 'operands': ['/items/1', '/items/2']}]
    tool = Spy()
    with pytest.raises(ValueError, match='targets must resolve'):
        guard_tool(tool, contract(schema, rules))
    assert tool.calls == []
