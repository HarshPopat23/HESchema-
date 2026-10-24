"""Explicit H60 rerun with independent scoring and durable, redacted request receipts.

Uses the frozen historical task pack: this is a replication, not untouched-task confirmation.
Credentials are read from an external mode-0600 file and are never recorded.
"""
import asyncio
import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
import run_60_tasks_experiment as base
from rescore_confirmation60 import correct

from heschema.study_evidence import atomic_json

OUT = Path(os.environ['H60_OUTPUT_DIR']).resolve()
KEY_FILE = Path(os.environ['H60_CREDENTIAL_FILE'])
original_evaluate = base.evaluate_attempt


def evaluate(raw, arm, case, contract, engine):
    result = original_evaluate(raw, arm, case, contract, engine)
    result['oracleCorrect'] = correct(raw, case, arm)
    return result


class RecordedClient:
    def __init__(self, key, worker_id):
        self.key = key
        self.worker_id = worker_id
        self.client = httpx.AsyncClient(timeout=90)

    async def generate(self, messages, model, max_tokens=2048, temperature=0.0):
        for attempt in range(12):
            identity = uuid.uuid4().hex
            path = OUT / 'request-evidence' / (identity + '.json')
            record = {
                'id': identity, 'worker': self.worker_id, 'model': model,
                'slot': self.slot, 'phase': 'repair' if len(messages) > 2 else 'initial',
                'startedAt': datetime.now(timezone.utc).isoformat(),
                'state': 'started', 'messages': messages,
                'maxTokens': max_tokens, 'temperature': temperature,
            }
            atomic_json(path, record)
            started = time.perf_counter()
            try:
                response = await self.client.post(
                    'https://api.groq.com/openai/v1/chat/completions',
                    headers={'Authorization': 'Bearer ' + self.key},
                    json={'model': model, 'messages': messages, 'max_tokens': max_tokens,
                          'temperature': temperature},
                )
                elapsed = (time.perf_counter() - started) * 1000
                record.update(statusCode=response.status_code, providerMs=elapsed)
                if response.status_code == 200:
                    data = response.json()
                    choice = data['choices'][0]
                    text = choice['message'].get('content') or ''
                    usage = data.get('usage', {})
                    # Do not retain private reasoning, authorization headers, or credentials.
                    record.update(state='returned', responseId=data.get('id'),
                                  resolvedModel=data.get('model'), finishReason=choice.get('finish_reason'),
                                  rawContent=text, usage=usage)
                    atomic_json(path, record)
                    return {'text': text, 'input_tokens': usage.get('prompt_tokens', 0),
                            'output_tokens': usage.get('completion_tokens', 0),
                            'latency_ms': elapsed, 'status_code': 200, 'error': None}
                record['state'] = 'failed'
                atomic_json(path, record)
                if response.status_code not in {429, 500, 502, 503, 504}:
                    raise RuntimeError(f'Provider rejected request: HTTP {response.status_code}; worker {self.worker_id}')
                try:
                    wait = max(60.0, float(response.headers.get('retry-after', 60)))
                except ValueError:
                    wait = 60.0
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                record.update(state='failed', errorType=type(exc).__name__,
                              providerMs=(time.perf_counter()-started)*1000)
                atomic_json(path, record)
                wait = min(60, 2**attempt)
            print(f'worker {self.worker_id}: retry wait {wait:.0f}s', flush=True)
            await asyncio.sleep(wait)
        raise RuntimeError('Retry budget exhausted; incomplete slots must remain incomplete')

    async def close(self):
        await self.client.aclose()


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    keys = [k.strip() for k in KEY_FILE.read_text().splitlines() if k.strip()]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate credentials')
    manifest = OUT / 'manifest.json'
    if manifest.exists():
        raise RuntimeError('Automatic resume disabled: inspect request evidence and pending repairs first')
    cases = (base.DATA_DIR / 'cases.json').read_bytes()
    frozen_code = {
        str(p.relative_to(base.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ('scripts', 'src/heschema')
        for p in sorted((base.ROOT / folder).rglob('*.py'))
    }
    atomic_json(manifest, {
        'study': 'H60 independent-oracle replication', 'caseSha256': hashlib.sha256(cases).hexdigest(),
        'oracleSha256': hashlib.sha256(Path(__file__).with_name('rescore_confirmation60.py').read_bytes()).hexdigest(),
        'runnerSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'models': base.MODELS, 'arms': base.ARMS, 'repeats': base.REPEATS,
        'workers': len(keys), 'mode': 'prompt_only', 'repairBudget': 1,
        'codeHashes': frozen_code,
        'schedule': base.build_schedule(json.loads(cases)),
        'limitations': ['historical source snapshots not independently recaptured',
                        'providerMs excludes local checks and quota waits',
                        'result rows retain historical detector decisions; oracle is independent'],
    })
    base.RUNS_DIR = OUT
    base.GroqClient = RecordedClient
    base.evaluate_attempt = evaluate
    base.get_groq_keys = lambda: keys
    asyncio.run(base.main())
