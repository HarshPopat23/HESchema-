"""Regression controls for resumed generation: intact responses are never regenerated."""
import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import finish_latency_study as finish  # noqa: E402


def test_saved_accepted_initial_makes_no_provider_call(tmp_path):
    slot = dict(caseId='saved', model='test-model', repeat=0, arm='A')
    (tmp_path/'cases.json').write_text(json.dumps([{'id':'saved'}]))
    fake_base = SimpleNamespace(
        ROOT=tmp_path, DATA_DIR=tmp_path,
        build_schedule=lambda cases,seed: [slot],
        build_messages_for_arm=lambda case,arm: ([],None),
    )

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, *args, **kwargs):
            raise AssertionError('Saved accepted response must not trigger generation')

    namespace = dict(vars(finish.study))
    namespace.update(base=fake_base, httpx=SimpleNamespace(AsyncClient=Client),
                     SchemaEngine=lambda:SimpleNamespace(close=lambda:None),
                     detector=lambda *args:(True,'',0.0))
    exec(finish.generation_source(),namespace)
    saved = {0:{'id':'preserved-provider-receipt','rawContent':'{}'}}
    out=tmp_path/'out'
    asyncio.run(namespace['execute'](out,['test-credential'],saved=saved))
    row=json.loads((out/'slots/0000.json').read_text())
    assert row['accepted'] is True
    assert row['requestIds']==['preserved-provider-receipt']
    assert row['resumedInitialId']=='preserved-provider-receipt'
    assert row['timing']['providerRoundTripMs']==0
    assert not list((out/'requests').glob('*.json'))
