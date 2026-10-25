"""A synchronous, dry-run-first boundary around the existing contract validator."""

import copy
import inspect

from .calculations import validate_with_calculations
from .context_schema import ContextError, check_context
from .diagnostics import diagnostic, parts
from .guard import load_contract
from .schema import SchemaEngine


def _approved_snapshot(snapshot):
    if not isinstance(snapshot, dict):
        raise ContextError('Provide an approved context snapshot from a trusted caller')
    snapshot = copy.deepcopy(snapshot)
    if (not isinstance(snapshot.get('id'), str) or not snapshot['id']
            or type(snapshot.get('version')) is not int or snapshot['version'] < 1
            or snapshot.get('confirmed') is not True
            or not isinstance(snapshot.get('data'), dict)):
        raise ContextError('Context needs id, positive integer version, confirmed=true and object data')
    pointers, facts = snapshot.get('approvedPointers', []), snapshot.get('facts', [])
    if not isinstance(pointers, list) or not isinstance(facts, list):
        raise ContextError('approvedPointers and facts must be lists')
    try:
        for pointer in pointers:
            parts(pointer)
        for fact in facts:
            if not isinstance(fact, dict) or fact.get('verified') is not True:
                raise ValueError('Each external fact must be explicitly verified')
            parts(fact['contextLocation'])
        check_context(snapshot)
    except (ValueError, TypeError, KeyError) as exc:
        raise ContextError('Invalid approved context: ' + str(exc)) from exc
    return snapshot


def run_workflow(contract, approved_context, output, *, dry_run=True, executor=None, engine=None):
    """Validate approved intent, then optionally call one synchronous executor.

    Defaults to dry-run. Refusals and schema-only acceptance cannot execute.
    The caller supplies trusted approval and owns authorization/transactions.
    Configuration, engine and executor exceptions propagate; no automatic retry.
    """
    if type(dry_run) is not bool:
        raise TypeError('dry_run must be a boolean')
    if executor is not None:
        if not callable(executor):
            raise TypeError('executor must be callable')
        if any(inspect.iscoroutinefunction(fn) or inspect.isasyncgenfunction(fn)
               or inspect.isgeneratorfunction(fn) for fn in (executor, getattr(executor, '__call__', None))):
            raise TypeError('run_workflow supports synchronous, non-generator executors only')
    if not dry_run and executor is None:
        raise ValueError('Execution requires an explicit executor')
    loaded = copy.deepcopy(load_contract(contract))
    report = {'status': 'rejected', 'validation': None, 'payload': None, 'diagnostics': [],
              'execution': {'attempted': False, 'status': 'blocked', 'result': None}}
    try:
        snapshot = _approved_snapshot(approved_context)
    except ContextError as exc:
        report['diagnostics'] = [diagnostic('CONTEXT_INVALID', 'context', message=str(exc), repair='needs_context')]
        return report
    owned_engine = engine is None
    validator = engine if engine is not None else SchemaEngine()
    try:
        try:
            result = validate_with_calculations(copy.deepcopy(output), validator, loaded, snapshot)
        except ContextError as exc:
            report['diagnostics'] = [diagnostic('CONTEXT_INVALID', 'context', message=str(exc), repair='needs_context')]
            return report
    finally:
        if owned_engine:
            validator.close()
    report['validation'] = result
    report['diagnostics'] = copy.deepcopy(result['errors'])
    parsed = result.get('parsed')
    if not result.get('accepted') or not result.get('success'):
        if not report['diagnostics']:
            report['diagnostics'].append(diagnostic(
                'EXECUTION_NOT_ELIGIBLE', 'execution', message=(
                    'Execution requires an accepted data payload checked against approved bindings; '
                    'schema-only, refusal and clarification outcomes cannot execute'
                ), repair='stop'))
        return report
    if loaded.outputKind == 'tool_envelope':
        if not isinstance(parsed, dict) or parsed.get('action') != 'call_tool' or parsed.get('tool') != loaded.tool:
            report['diagnostics'].append(diagnostic('EXECUTION_NOT_ELIGIBLE', 'execution', repair='stop'))
            return report
        payload = parsed.get('arguments')
    else:
        payload = parsed
    if not isinstance(payload, dict):
        report['diagnostics'].append(diagnostic(
            'PAYLOAD_UNSUPPORTED', 'execution', message='This workflow supports object payloads only', repair='stop'))
        return report
    report['payload'] = copy.deepcopy(payload)
    if dry_run:
        report.update(status='dry_run', execution={'attempted': False, 'status': 'not_requested', 'result': None})
        return report
    # Catch expiry during validation. This cannot make a remote action atomic
    # with a context store; the application must enforce that in its transaction.
    try:
        check_context(snapshot)
    except (ContextError, ValueError, TypeError) as exc:
        report['diagnostics'].append(diagnostic('CONTEXT_INVALID', 'context', message=str(exc), repair='needs_context'))
        return report
    callback_result = executor(copy.deepcopy(payload))
    if inspect.isawaitable(callback_result) or inspect.isgenerator(callback_result) or inspect.isasyncgen(callback_result):
        if inspect.iscoroutine(callback_result) or inspect.isgenerator(callback_result):
            callback_result.close()
        raise TypeError('Executor returned deferred work; use a synchronous executor. It was invoked once; do not retry blindly')
    report.update(status='executed', execution={'attempted': True, 'status': 'completed', 'result': callback_result})
    return report
