"""Failure-policy configuration and side-effect boundaries for legacy decorators."""
import asyncio
import importlib

import pytest

from heschema import ContractViolationError, guard

SCHEMA = {'type': 'object', 'properties': {'x': {'type': 'integer'}, 'y': {'type': 'integer'}},
          'required': ['x', 'y'], 'additionalProperties': False}
CONTRACT = {'id': 'policy-counter', 'version': '1', 'schema': SCHEMA,
            'relationships': [{'id': 'match', 'kind': 'equals', 'left': '/x', 'right': '/y'}]}


def function_and_calls(is_async):
    calls = []
    if is_async:
        async def function(x, y):
            calls.append((x, y))
            return x
    else:
        def function(x, y):
            calls.append((x, y))
            return x
    return function, calls


def invoke(function, is_async, *args):
    return asyncio.run(function(*args)) if is_async else function(*args)


@pytest.mark.parametrize('is_async', [False, True])
@pytest.mark.parametrize('policy', ['typo', '', 'RAISE', None, False, 0, [], {}])
def test_invalid_policy_is_rejected_before_any_wrapper_exists(is_async, policy):
    function, calls = function_and_calls(is_async)
    with pytest.raises(ValueError, match='on_fail.*raise.*refuse.*repair'):
        guard(CONTRACT, on_fail=policy)(function)
    assert calls == []


def test_invalid_policy_is_rejected_before_contract_or_engine_resolution(monkeypatch):
    module = importlib.import_module('heschema.guard')
    def unexpected(*args, **kwargs):
        pytest.fail('Invalid policy must be rejected before loading the contract or engine')
    monkeypatch.setattr(module, 'load_contract', unexpected)
    monkeypatch.setattr(module, 'get_default_engine', unexpected)
    with pytest.raises(ValueError, match='on_fail'):
        guard('a-contract-that-must-not-be-read.json', on_fail='typo')


@pytest.mark.parametrize('is_async', [False, True])
@pytest.mark.parametrize('policy', ['raise', 'refuse', 'repair'])
@pytest.mark.parametrize('failure', ['schema', 'relationship', 'context', 'calculation'])
def test_all_supported_rejection_policies_invoke_zero_times(is_async, policy, failure):
    function, calls = function_and_calls(is_async)
    definition = dict(CONTRACT)
    values = (1, 2) if failure == 'relationship' else ('wrong', 1)
    if failure == 'context':
        definition['bindings'] = [{'instanceLocation': '/x', 'contextLocation': '/x'}]
        values = (1, 1)
    elif failure == 'calculation':
        definition['relationships'] = [{'id': 'calculate', 'kind': 'product_equals',
                                       'operands': ['/x', '/x'], 'target': '/y', 'compute': 'application'}]
    wrapped = guard(definition, on_fail=policy)(function)
    if policy == 'refuse':
        result = invoke(wrapped, is_async, *values)
        assert result['action'] == 'refuse'
        assert not result['validation']['accepted']
    else:
        with pytest.raises(ContractViolationError):
            invoke(wrapped, is_async, *values)
    assert calls == []


@pytest.mark.parametrize('is_async', [False, True])
@pytest.mark.parametrize('policy', ['raise', 'refuse', 'repair'])
def test_supported_policies_preserve_one_accepted_invocation(is_async, policy):
    function, calls = function_and_calls(is_async)
    wrapped = guard(CONTRACT, on_fail=policy)(function)
    assert invoke(wrapped, is_async, 3, 3) == 3
    assert calls == [(3, 3)]


@pytest.mark.parametrize('is_async', [False, True])
def test_default_policy_rejects_before_invocation(is_async):
    function, calls = function_and_calls(is_async)
    wrapped = guard(CONTRACT)(function)
    with pytest.raises(ContractViolationError):
        invoke(wrapped, is_async, 'wrong', 1)
    assert calls == []
