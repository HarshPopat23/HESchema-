"""Shared bounded repair. Feedback is supplied by runtime checks, never a scoring oracle."""

import asyncio
import copy
import inspect
import time
from dataclasses import asdict, dataclass

from .context_schema import ContextError
from .diagnostics import runtime_feedback
from .jsonio import canonical
from .providers import Generation, ProviderError


@dataclass(frozen=True)
class RepairLimits:
    repairs: int = 0
    max_requests: int | None = None
    max_tokens: int = 1024
    token_budget: int | None = None
    deadline_seconds: float = 180
    feedback_chars: int = 4000

    def __post_init__(self):
        if not 0 <= self.repairs <= 5 or self.max_tokens < 1 or self.deadline_seconds <= 0 or self.feedback_chars < 128:
            raise ValueError('Invalid repair limits')
        if self.max_requests is not None and self.max_requests < 0:
            raise ValueError('Request budget cannot be negative')
        if self.token_budget is not None and self.token_budget < 0:
            raise ValueError('Token budget cannot be negative')


async def request_generation(provider, messages, seed, max_tokens, temperature, schema=None):
    """Disable transport retries; every request is budgeted by the coordinator."""
    parameters = inspect.signature(provider.generate).parameters
    kwargs = {}
    variadic = any(p.kind == p.VAR_KEYWORD for p in parameters.values())
    if 'retry' in parameters or variadic:
        kwargs['retry'] = False
    if schema is not None:
        if 'format_schema' not in parameters and not variadic:
            raise ProviderError('Native mode unavailable on this adapter', code='unsupported_mode', requests=0)
        kwargs['format_schema'] = schema
    return await provider.generate(messages, seed, max_tokens, temperature, **kwargs)


def feedback_message(errors, style='actionable', max_chars=4000):
    if style not in {'generic', 'raw', 'actionable'}:
        raise ValueError('Unknown feedback style')
    if style == 'generic':
        return 'The final output failed validation. Return corrected whole JSON using the same contract and approved context.'
    entries = []
    for error in errors:
        if style == 'raw':
            entry = error
        else:
            entry = {k: error[k] for k in ('code', 'stage', 'instanceLocation', 'schemaLocation', 'ruleId', 'kind', 'message', 'actual', 'expected', 'inputLocations', 'protectedInputs', 'repair') if k in error}
            if error.get('details'):
                entry['branches'] = [{k: e[k] for k in ('instanceLocation', 'schemaLocation', 'message') if k in e} for e in error['details'][:6]]
        candidate = [*entries, entry]
        if len(canonical(candidate)) > max_chars - 100:
            break
        entries = candidate
    return ('Correct these validation failures using only the approved context: ' + canonical(entries))[:max_chars]


async def coordinate(generate, evaluate, messages, *, limits=None, feedback_style='actionable',
                     feedback_selector=None, context_check=None, cancel_event=None, first_generation=None):
    limits = limits or RepairLimits()
    if feedback_style not in {'generic', 'raw', 'actionable'}:
        raise ValueError('Unknown feedback style')
    selector = feedback_selector or (lambda e: runtime_feedback(e.get('errors', []), allow_state=True))
    messages = copy.deepcopy(messages)
    attempts, ledger = [], []
    first = final = None
    requests = reserved_tokens = 0
    started = time.perf_counter()
    stop, failure = 'exhausted', None

    def checkpoint():
        if context_check:
            context_check()
        if cancel_event is not None and cancel_event.is_set():
            raise asyncio.CancelledError

    for index in range(limits.repairs + 1):
        generated = first_generation if index == 0 else None
        elapsed = time.perf_counter() - started
        if elapsed >= limits.deadline_seconds:
            stop = 'deadline'
            break
        if generated is None and ((limits.max_requests is not None and requests >= limits.max_requests) or
                                  (limits.token_budget is not None and reserved_tokens + limits.max_tokens > limits.token_budget)):
            stop = 'request_budget' if limits.max_requests is not None and requests >= limits.max_requests else 'token_budget'
            break
        request_started = time.perf_counter()
        request_record = {'attempt': index, 'requestMade': generated is None, 'status': 'started'}
        try:
            checkpoint()
            if generated is None:
                requests += 1
                reserved_tokens += limits.max_tokens
                ledger.append(request_record)
                remaining = limits.deadline_seconds - (time.perf_counter() - started)
                task = asyncio.create_task(generate(messages, index))
                cancelled = asyncio.create_task(cancel_event.wait()) if cancel_event is not None else None
                try:
                    waiting = {task} | ({cancelled} if cancelled else set())
                    done, _ = await asyncio.wait(waiting, timeout=max(0, remaining), return_when=asyncio.FIRST_COMPLETED)
                    if cancelled is not None and cancelled in done:
                        raise asyncio.CancelledError
                    if task not in done:
                        raise TimeoutError
                    generated = await task
                finally:
                    for pending in (task, cancelled):
                        if pending is not None and not pending.done():
                            pending.cancel()
                            await asyncio.gather(pending, return_exceptions=True)
                # Adapters used here must disable transport retries. Still record any reported calls.
                requests += generated.transport_retries
                request_record.update(status='returned', generation=generated.diagnostic())
            else:
                request_record.update(status='replayed', generation=generated.diagnostic())
                ledger.append(request_record)
            checkpoint()
            evaluation = evaluate(generated)
            if inspect.isawaitable(evaluation):
                evaluation = await evaluation
            checkpoint()
            attempts.append({'generation': asdict(generated), 'evaluation': evaluation, 'requestMade': request_record['requestMade']})
            first = evaluation if first is None else first
            final = evaluation
            action = (evaluation.get('parsed') or {}).get('action') if isinstance(evaluation.get('parsed'), dict) else None
            if generated.completion == 'truncated':
                stop = 'truncated'
                break
            if action in {'refuse', 'ask_clarification'} and evaluation.get('referenceSchemaValid'):
                stop = action
                break
            if evaluation.get('accepted', evaluation.get('success', False)):
                stop = 'valid'
                break
            if any(e.get('repair') in {'needs_context', 'stop'} for e in evaluation.get('errors', [])):
                stop = 'needs_context' if any(e.get('repair') == 'needs_context' for e in evaluation['errors']) else 'nonrecoverable'
                break
            feedback = selector(evaluation)
            if not feedback and generated.completion == 'empty':
                feedback = [{'code': 'OUTPUT_EMPTY', 'message': 'No final content was returned; reasoning is not output'}]
            if not feedback:
                stop = 'no_runtime_feedback'
                break
            if index < limits.repairs:
                messages.extend([{'role': 'assistant', 'content': generated.text},
                                 {'role': 'user', 'content': feedback_message(feedback, feedback_style, limits.feedback_chars)}])
        except ContextError as exc:
            request_record['status'] = 'context_changed'
            failure = {'code': 'context_changed', 'message': str(exc)[:500]}
            stop = 'context_changed'
            break
        except ProviderError as exc:
            request_record.update(status=exc.code, failure=exc.diagnostic())
            requests += exc.requests - 1
            if exc.requests == 0:
                request_record['requestMade'] = False
                reserved_tokens -= limits.max_tokens
            failure = exc.diagnostic()
            stop = exc.code
            break
        except TimeoutError:
            request_record['status'] = 'deadline'
            failure = {'code': 'deadline', 'message': 'Run deadline reached'}
            stop = 'deadline'
            break
        except asyncio.CancelledError:
            request_record['status'] = 'cancelled'
            stop = 'cancelled'
            break
        finally:
            request_record['elapsedMs'] = (time.perf_counter() - request_started) * 1000
    try:
        checkpoint()
    except (ContextError, asyncio.CancelledError) as exc:
        stop = 'context_changed' if isinstance(exc, ContextError) else 'cancelled'
        failure = {'code': stop, 'message': str(exc)[:500]}
    if first is None:
        try:
            first = evaluate(Generation(''))
            if inspect.isawaitable(first):
                first = await first
        except ContextError:
            first = {'result': 'NOT_EVALUATED', 'success': False, 'accepted': False,
                     'outputPresent': False, 'stages': dict.fromkeys(('json', 'originalSchema', 'effectiveSchema', 'context', 'relationships'), 'not_evaluated'),
                     'referenceSchemaValid': None, 'semanticValid': None, 'intentScope': 'not_checked',
                     'errors': [], 'parsed': None, 'validationMs': 0, 'executionAuthorized': False}
    final = final or first
    if stop in {'context_changed', 'cancelled', 'deadline', 'request_budget', 'token_budget'}:
        final = {**final, 'success': False, 'accepted': False, 'result': 'FAIL' if attempts else 'NOT_EVALUATED', 'stopReason': stop}
        if stop == 'context_changed':
            final['result'] = 'STALE_CONTEXT'
            final['semanticValid'] = None
            final['stages'] = {**final.get('stages', {}), 'context': 'unknown'}
    return {'firstEvaluation': first, 'finalEvaluation': final, 'attempts': attempts,
            'requestLedger': ledger, 'requestsAttempted': requests, 'repairAttempts': max(0, len(ledger) - 1),
            'reservedOutputTokens': reserved_tokens, 'limits': asdict(limits), 'feedbackStyle': feedback_style,
            'stopReason': stop, 'failure': failure, 'elapsedMs': (time.perf_counter() - started) * 1000}
