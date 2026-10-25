"""Offline engineering example: the executor records a value in a local list only.

Install the checkout with `pip install -e '.[dev]'`, then run this file. The
confirmed snapshot is a test fixture, not evidence of an external human approval.
"""
import json

from heschema import Contract, run_workflow


def main():
    contract = Contract(
        id='trip-workflow-example', version='1',
        schema={'type': 'object', 'properties': {
            'destination': {'type': 'string'}, 'travellers': {'type': 'integer', 'minimum': 1}},
            'required': ['destination', 'travellers'], 'additionalProperties': False},
        contextSchema={'type': 'object'},
        bindings=[{'instanceLocation': '/' + name, 'contextLocation': '/' + name}
                  for name in ('destination', 'travellers')],
    )
    # In an application, retrieve this from its trusted, explicitly approved store.
    approved = {'id': 'example-context', 'version': 1, 'confirmed': True,
                'contractHash': contract.identity['hash'],
                'data': {'destination': 'Goa', 'travellers': 2},
                'approvedPointers': ['/destination', '/travellers'], 'facts': []}
    calls = []
    def record_trip(payload):
        calls.append(payload)
        return {'recorded': True}
    raw = '{"destination":"Goa","travellers":2}'
    preview = run_workflow(contract, approved, raw, executor=record_trip)
    assert preview['status'] == 'dry_run' and not calls
    rejected = run_workflow(contract, approved, '{"destination":"Pune","travellers":2}',
                            dry_run=False, executor=record_trip)
    assert rejected['status'] == 'rejected' and not calls
    executed = run_workflow(contract, approved, raw, dry_run=False, executor=record_trip)
    assert executed['status'] == 'executed' and len(calls) == 1
    summary = {'preview': preview['status'], 'rejected': rejected['status'],
               'rejectionCodes': [error['code'] for error in rejected['diagnostics']],
               'execution': executed['status'], 'executorCalls': len(calls), 'payload': calls[0]}
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    main()
