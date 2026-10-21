"""Resume into a new directory with slower pacing and a preserved session history.

Never edits the original checkpoint/config or changes generation settings. The
frozen protocol specifies a minimum interval; a longer interval is operational.
"""

import argparse
import asyncio
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from heschema.confirmation import PACK, sha, verify_freeze
from heschema.confirmation_run import execute


def prepare_resume(previous, target, interval):
    previous, target = Path(previous), Path(target)
    config = json.loads((previous / 'config.json').read_text())
    verify_freeze()
    if config['freezeSha256'] != sha(PACK / 'freeze.json'):
        raise ValueError('Cannot import another study')
    if interval < config['interval']:
        raise ValueError('This operation only permits slower pacing')
    root = Path(__file__).resolve().parents[1]
    if any(sha(root / path) != value for path, value in config['codeHashes'].items()):
        raise ValueError('Runtime changed; cannot resume this measured implementation')
    if target.exists():
        raise ValueError('Use a new destination; never overwrite evidence')
    target.mkdir(parents=True)
    for name in ('runs.jsonl', 'events.jsonl', 'environment.json', 'environment-prior.json', 'transport_events.jsonl'):
        if (previous / name).exists():
            shutil.copyfile(previous / name, target / name)
    history_path = previous / 'session_history.json'
    history = json.loads(history_path.read_text()) if history_path.exists() else []
    history.append({'priorConfig': config,
                    'priorEnvironment': json.loads((previous / 'environment.json').read_text()) if (previous / 'environment.json').exists() else None,
                    'priorSummary': json.loads((previous / 'summary.json').read_text()),
                    'priorJournalSha256': sha(previous / 'runs.jsonl'),
                    'recordedBeforeResumeAt': datetime.now(timezone.utc).isoformat(),
                    'nextWorkerIntervalSeconds': interval,
                    'reason': 'Quota stop; slower pacing after cooldown. Same frozen tasks, model settings and authorized credential pool. Completed slots are retained, pending repair replays its saved initial output.'})
    stop_path = previous / 'execution_stop.json'
    if stop_path.exists():
        stop = json.loads(stop_path.read_text())
        history[-1]['priorExecutionStop'] = stop
        history[-1]['reason'] = 'Resume after documented execution stop; preserve incomplete request accounting.'
        if stop.get('interruption'):
            history[-1]['interruption'] = stop['interruption']
    (target / 'session_history.json').write_text(json.dumps(history, indent=2) + '\n')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('previous', type=Path)
    parser.add_argument('target', type=Path)
    parser.add_argument('--interval', type=float, default=30)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if not args.execute:
        parser.error('Explicit --execute required; wait for provider quota recovery before resuming')
    destination = prepare_resume(args.previous, args.target, args.interval)
    print(json.dumps(asyncio.run(execute(destination, interval=args.interval)), indent=2))
