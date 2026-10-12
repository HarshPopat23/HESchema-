import asyncio
import copy

import pytest
from test_relationships import CTX, INVOICE

from heschema.context_schema import ContextError
from heschema.jsonio import canonical
from heschema.providers import Generation, ProviderError
from heschema.repair import RepairLimits, coordinate
from heschema.schema import SchemaEngine
from heschema.validation import validate_contract

GOOD = {'quantity': 2, 'unitPriceMinor': 1250, 'totalMinor': 2500}
BAD = {**GOOD, 'totalMinor': 25}


def check(g):
    return validate_contract(g.text, SchemaEngine(), INVOICE, CTX, generation=g)


def test_repair_uses_authorized_derived_error_and_counts_every_request():
    seen = []
    async def request(messages, index):
        seen.append(copy.deepcopy(messages))
        return Generation(canonical(BAD if index == 0 else GOOD), 5, 10, 'mock', metadata={'finish_reason': 'stop'})
    result = asyncio.run(coordinate(request, check, [{'role': 'user', 'content': 'Invoice'}], limits=RepairLimits(2)))
    assert result['finalEvaluation']['success'] and result['requestsAttempted'] == 2
    assert result['repairAttempts'] == 1 and len(result['requestLedger']) == 2
    assert '2500' in seen[1][-1]['content']
    assert result['limits']['repairs'] == 2


def test_exhaustion_refusal_clarification_and_known_truncation_stop():
    async def bad(messages, index):
        return Generation(canonical(BAD))
    result = asyncio.run(coordinate(bad, check, [], limits=RepairLimits(1)))
    assert result['stopReason'] == 'exhausted' and not result['finalEvaluation']['success']
    async def truncated(messages, index):
        return Generation(canonical(GOOD), metadata={'finish_reason': 'length'})
    result = asyncio.run(coordinate(truncated, check, [], limits=RepairLimits(3)))
    assert result['stopReason'] == 'truncated' and result['requestsAttempted'] == 1
    from heschema.contracts import Contract
    from heschema.validation import envelope
    c = Contract('control', '1', {'type': 'object'}, 'tool_envelope', 't')
    for action in ['refuse', 'ask_clarification']:
        async def control(messages, index):
            return Generation(canonical(envelope(action, missing=['x'] if action == 'ask_clarification' else [])))
        r = asyncio.run(coordinate(control, lambda g: validate_contract(g.text, SchemaEngine(), c), [], limits=RepairLimits(3)))
        assert r['stopReason'] == action and r['requestsAttempted'] == 1


def test_stale_context_cancellation_deadline_and_budgets():
    async def check_flow():
        stale = False
        def checkpoint():
            if stale:
                raise ContextError('Stale context version')
        async def changed(messages, index):
            nonlocal stale
            stale = True
            return Generation(canonical(GOOD))
        r = await coordinate(changed, check, [], limits=RepairLimits(2), context_check=checkpoint)
        assert r['stopReason'] == 'context_changed' and not r['finalEvaluation']['success']
        assert r['requestsAttempted'] == 1 and r['requestLedger'][0]['status'] == 'context_changed'
        cancel = asyncio.Event()
        async def blocked(messages, index):
            cancel.set()
            await asyncio.Event().wait()
        r = await coordinate(blocked, check, [], cancel_event=cancel)
        assert r['stopReason'] == 'cancelled' and r['requestsAttempted'] == 1
        async def slow(messages, index):
            await asyncio.Event().wait()
        r = await coordinate(slow, check, [], limits=RepairLimits(deadline_seconds=.01))
        assert r['stopReason'] == 'deadline' and r['requestsAttempted'] == 1
        async def invalid(messages, index):
            return Generation(canonical(BAD))
        r = await coordinate(invalid, check, [], limits=RepairLimits(2, max_requests=1))
        assert r['stopReason'] == 'request_budget' and r['requestsAttempted'] == 1
        r = await coordinate(invalid, check, [], limits=RepairLimits(2, token_budget=0))
        assert r['stopReason'] == 'token_budget' and r['requestsAttempted'] == 0
    asyncio.run(check_flow())


def test_rejected_request_is_not_retried_and_replayed_first_output_is_free():
    async def rejected(messages, index):
        raise ProviderError('HTTP 400', code='request_rejected', status=400)
    r = asyncio.run(coordinate(rejected, check, [], limits=RepairLimits(5)))
    assert r['requestsAttempted'] == 1 and r['stopReason'] == 'request_rejected'
    assert r['firstEvaluation']['stages']['json'] == 'not_evaluated'
    async def fixed(messages, index):
        return Generation(canonical(GOOD))
    r = asyncio.run(coordinate(fixed, check, [], first_generation=Generation(canonical(BAD)), limits=RepairLimits(1)))
    assert r['requestsAttempted'] == 1 and r['finalEvaluation']['success']
    assert not r['requestLedger'][0]['requestMade']
    with pytest.raises(ValueError):
        RepairLimits(6)
