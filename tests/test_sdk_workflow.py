"""Side-effect counters verify the public SDK execution boundary."""
import copy
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from heschema import Contract, run_workflow
from heschema.schema import SchemaEngine


def contract(output_kind='document', calculation=False):
    return Contract(
        'sdk-invoice', '1',
        {'type': 'object', 'properties': {
            'quantity': {'type': 'integer', 'minimum': 1},
            'price': {'type': 'integer', 'minimum': 0},
            'invoice': {'type': 'object', 'properties': {
                'a/b~c': {'type': 'integer'}, 'note': {'type': 'string'}},
                'required': ['a/b~c', 'note'], 'additionalProperties': False}},
         'required': ['quantity', 'price', 'invoice'], 'additionalProperties': False},
        outputKind=output_kind, tool='prepare_invoice' if output_kind == 'tool_envelope' else None,
        contextSchema={'type': 'object'},
        bindings=[{'instanceLocation': '/' + key, 'contextLocation': '/' + key} for key in ('quantity', 'price')],
        relationships=[{'id': 'total', 'kind': 'product_equals', 'operands': ['/quantity', '/price'],
                        'target': '/invoice/a~1b~0c', **({'compute': 'application'} if calculation else {})}],
    )


def snapshot(c):
    return {'id': 'approved-invoice', 'version': 1, 'confirmed': True,
            'contractHash': c.identity['hash'], 'data': {'quantity': 2, 'price': 7},
            'approvedPointers': ['/quantity', '/price'], 'facts': []}


def output(c, action='call_tool'):
    doc = {'quantity': 2, 'price': 7, 'invoice': {'a/b~c': 14, 'note': 'preserve'}}
    if c.outputKind == 'document':
        return doc
    return {'action': action, 'tool': c.tool if action == 'call_tool' else None,
            'arguments': doc if action == 'call_tool' else {},
            'missingFields': ['quantity'] if action == 'ask_clarification' else [], 'reason': 'example'}


@pytest.mark.parametrize('kind', ['document', 'tool_envelope'])
@pytest.mark.parametrize('raw', [False, True])
def test_default_dry_run_and_explicit_execution(kind, raw):
    c = contract(kind)
    ctx, doc = snapshot(c), output(c)
    before = copy.deepcopy((c.as_dict(), ctx, doc))
    executor = Mock(return_value={'saved': True})
    supplied = json.dumps(doc) if raw else doc
    preview = run_workflow(c, ctx, supplied, executor=executor)
    assert preview['status'] == 'dry_run'
    assert preview['validation']['accepted'] and preview['validation']['success']
    assert not preview['validation']['executionAuthorized']
    assert not preview['execution']['attempted']
    executor.assert_not_called()
    result = run_workflow(c, ctx, supplied, dry_run=False, executor=executor)
    assert result['status'] == 'executed'
    executor.assert_called_once_with(doc['arguments'] if kind == 'tool_envelope' else doc)
    assert result['execution']['result'] == {'saved': True}
    assert (c.as_dict(), ctx, doc) == before


@pytest.mark.parametrize('failure', ['json', 'source', 'relationship', 'missing-binding', 'unconfirmed',
                                    'expired', 'contract-hash', 'missing-context', 'malformed-context',
                                    'truthy-approval', 'duplicate-key', 'wrong-tool'])
def test_rejections_cause_zero_executor_invocations(failure):
    c = contract('tool_envelope' if failure == 'wrong-tool' else 'document')
    ctx, doc = snapshot(c), output(c)
    if failure == 'json':
        doc = '{'
    elif failure == 'source':
        doc['quantity'] = 3
    elif failure == 'relationship':
        doc['invoice']['a/b~c'] = 13
    elif failure == 'missing-binding':
        ctx['approvedPointers'] = ['/quantity']
    elif failure == 'unconfirmed':
        ctx['confirmed'] = False
    elif failure == 'expired':
        ctx['expiresAt'] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    elif failure == 'contract-hash':
        ctx['contractHash'] = 'different'
    elif failure == 'missing-context':
        ctx = None
    elif failure == 'malformed-context':
        ctx['facts'] = [{}]
    elif failure == 'truthy-approval':
        ctx['confirmed'] = 'yes'
    elif failure == 'duplicate-key':
        doc = '{"quantity":2,"quantity":3}'
    elif failure == 'wrong-tool':
        doc['tool'] = 'other_tool'
    executor = Mock()
    report = run_workflow(c, ctx, doc, dry_run=False, executor=executor)
    assert report['status'] == 'rejected'
    assert report['diagnostics']
    assert not report['execution']['attempted']
    executor.assert_not_called()


@pytest.mark.parametrize('action', ['refuse', 'ask_clarification'])
def test_accepted_control_response_is_not_executable(action):
    c = contract('tool_envelope')
    executor = Mock()
    report = run_workflow(c, snapshot(c), output(c, action), dry_run=False, executor=executor)
    assert report['validation']['accepted']
    assert report['status'] == 'rejected'
    executor.assert_not_called()


def test_schema_only_acceptance_is_not_executable():
    c = Contract('schema-only', '1', {'type': 'object'})
    executor = Mock()
    report = run_workflow(c, snapshot(c), {}, dry_run=False, executor=executor)
    assert report['validation']['accepted'] and not report['validation']['success']
    assert report['status'] == 'rejected'
    executor.assert_not_called()


@pytest.mark.parametrize('kind', ['document', 'tool_envelope'])
def test_declared_calculation_passes_intact_nested_payload(kind):
    c = contract(kind, calculation=True)
    doc = output(c)
    payload = doc['arguments'] if kind == 'tool_envelope' else doc
    del payload['invoice']['a/b~c']
    before = copy.deepcopy(doc)
    executor = Mock(return_value='done')
    report = run_workflow(c, snapshot(c), json.dumps(doc), dry_run=False, executor=executor)
    assert report['validation']['calculation']['status'] == 'applied'
    assert report['status'] == 'executed'
    assert executor.call_args.args[0]['invoice'] == {'a/b~c': 14, 'note': 'preserve'}
    assert doc == before


def test_executor_mutation_does_not_modify_diagnostics_or_caller_input():
    c = contract()
    doc = output(c)
    def executor(payload):
        payload['invoice']['note'] = 'changed'
    report = run_workflow(c, snapshot(c), doc, dry_run=False, executor=executor)
    assert doc['invoice']['note'] == report['payload']['invoice']['note'] == 'preserve'
    assert report['validation']['parsed']['invoice']['note'] == 'preserve'


def test_callback_failure_propagates_without_retry():
    c = contract()
    executor = Mock(side_effect=RuntimeError('application failed'))
    with pytest.raises(RuntimeError, match='application failed'):
        run_workflow(c, snapshot(c), output(c), dry_run=False, executor=executor)
    executor.assert_called_once()


@pytest.mark.parametrize('bad_flag', [0, 1, None, 'false'])
def test_invalid_dry_run_policy_never_invokes_executor(bad_flag):
    executor = Mock()
    with pytest.raises(TypeError, match='dry_run'):
        run_workflow(contract(), None, {}, dry_run=bad_flag, executor=executor)
    executor.assert_not_called()


def test_missing_or_async_executor_fails_before_calling():
    c = contract()
    with pytest.raises(ValueError, match='explicit executor'):
        run_workflow(c, snapshot(c), output(c), dry_run=False)
    calls = []
    async def asynchronous(payload):
        calls.append(payload)
    with pytest.raises(TypeError, match='synchronous'):
        run_workflow(c, snapshot(c), output(c), dry_run=False, executor=asynchronous)
    assert calls == []


def test_approval_expiry_is_rechecked_before_execution(monkeypatch):
    import heschema.workflow as workflow
    c = contract()
    executor = Mock()
    checks = Mock(side_effect=[None, ValueError('approval expired after validation')])
    monkeypatch.setattr(workflow, 'check_context', checks)
    report = run_workflow(c, snapshot(c), output(c), dry_run=False, executor=executor)
    assert report['validation']['accepted']
    assert report['status'] == 'rejected'
    executor.assert_not_called()


def test_borrowed_engine_remains_open():
    c = contract()
    engine = SchemaEngine()
    engine.close = Mock(wraps=engine.close)
    run_workflow(c, snapshot(c), output(c), engine=engine)
    engine.close.assert_not_called()
    engine.close()


def test_object_payload_support_limit_never_invokes_executor():
    c = Contract('array-document', '1', {'type': 'array'},
                 bindings=[{'instanceLocation': '', 'contextLocation': '/items'}])
    ctx = {'id': 'array-context', 'version': 1, 'confirmed': True,
           'data': {'items': [1, 2]}, 'approvedPointers': ['/items']}
    executor = Mock()
    report = run_workflow(c, ctx, '[1,2]', dry_run=False, executor=executor)
    assert report['validation']['success']
    assert report['status'] == 'rejected'
    assert report['diagnostics'][-1]['code'] == 'PAYLOAD_UNSUPPORTED'
    executor.assert_not_called()


def test_owned_engine_closes_on_validation_failure(monkeypatch):
    import heschema.workflow as workflow
    c = contract()
    engine = SchemaEngine()
    engine.close = Mock(wraps=engine.close)
    monkeypatch.setattr(workflow, 'SchemaEngine', lambda: engine)
    report = run_workflow(c, snapshot(c), '{')
    assert report['status'] == 'rejected'
    engine.close.assert_called_once()


def test_offline_example_runs_and_has_one_local_side_effect():
    import runpy
    from pathlib import Path
    namespace = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'examples/sdk/workflow.py'))
    assert namespace['main']()['executorCalls'] == 1
