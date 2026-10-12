"""Run with `python examples/contracts/walkthrough.py`; offline synthetic outcomes only."""

import asyncio
import json
import tempfile
from pathlib import Path

from heschema.context_schema import check_context
from heschema.jsonio import canonical, read_json
from heschema.providers import Generation
from heschema.registry import ContractRegistry
from heschema.repair import RepairLimits, coordinate
from heschema.schema import SchemaEngine
from heschema.state import StateStore
from heschema.validation import validate_contract


async def main():
    registry, engine = ContractRegistry(), SchemaEngine()
    example = read_json(Path(__file__).with_name('invoice.json'))
    contract = registry.register(example['contract'])
    with tempfile.TemporaryDirectory() as directory:
        store = StateStore(Path(directory) / 'state.sqlite')
        context = store.create_context('demo-operator', contract, **{
            'data': example['context']['data'], 'approved_pointers': example['context']['approvedPointers']})
        context = store.confirm_context(context['id'], 'demo-operator', context['version'])
        decisions = {name: validate_contract(example[key], engine, contract, context)
                     for name, key in [('allowed', 'validOutput'), ('rejected', 'invalidOutput')]}
        decisions['missing_context'] = validate_contract(example['validOutput'], engine, contract)
        async def synthetic(messages, attempt):
            # Explicitly fake outputs exercise the pipeline, not empirical recovery.
            return Generation(canonical(example['invalidOutput' if attempt == 0 else 'validOutput']),
                              0, 0, 'offline-demo', metadata={'synthetic': True, 'finish_reason': 'stop'})
        decisions['repaired'] = await coordinate(synthetic, lambda g: validate_contract(g.text, engine, contract, context, generation=g),
                                                [{'role': 'user', 'content': example['prompt']}], limits=RepairLimits(1))
        store.invalidate_context(context['id'], 'demo-operator', context['version'])
        try:
            check_context(store.get_context(context['id'], 'demo-operator'), version=context['version'])
        except ValueError as error:
            decisions['stale_context'] = {'result': 'STALE_CONTEXT', 'message': str(error), 'executionAuthorized': False}
        print(json.dumps({'provenance': 'synthetic_offline_walkthrough', 'empiricalLLMEvidence': False, 'decisions': decisions}, indent=2))
    engine.close()


if __name__ == '__main__':
    asyncio.run(main())
