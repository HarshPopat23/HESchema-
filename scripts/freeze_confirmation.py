"""Audit and freeze once, before any model inference. Refuses to overwrite a freeze."""

import hashlib
import json
import subprocess
from datetime import datetime, timezone

from heschema.confirmation import PACK, audit, frozen_files


def main():
    if (PACK / 'freeze.json').exists():
        raise ValueError('Already frozen; use a new version for protocol amendments')
    baseline = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', baseline,
                                     'research', 'benchmarks', 'tests'], text=True).splitlines()
    corpus = []
    prior_prompts, prior_facts = set(), set()
    needles = ['nodejs/Release', 'endoflife.date/api/python', 'spdx/license-list-data',
               'iana.org/assignments/media-types/application.csv',
               'prometheus-operator/prometheus-operator', 'formulae.brew.sh/api/formula/']
    hits = []

    def digest(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

    def visit(value):
        if isinstance(value, dict):
            if isinstance(value.get('prompt'), str):
                prior_prompts.add(digest(value['prompt']))
            for key in ('context', 'snapshot'):
                if isinstance(value.get(key), dict) and 'data' in value[key]:
                    prior_facts.add(digest(value[key]['data']))
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    for path in paths:
        raw = subprocess.check_output(['git', 'show', baseline + ':' + path])
        corpus.append({'path': path, 'sha256': hashlib.sha256(raw).hexdigest()})
        if path.endswith(('.json', '.jsonl', '.md', '.py')):
            text = raw.decode(errors='replace')
            found = [needle for needle in needles if needle in text]
            if found:
                hits.append({'path': path, 'sourceIdentifiers': found})
            if path.endswith('.json'):
                try:
                    visit(json.loads(text))
                except ValueError:
                    pass
            elif path.endswith('.jsonl'):
                for line in text.splitlines():
                    try:
                        visit(json.loads(line))
                    except ValueError:
                        pass
    cases = json.loads((PACK / 'cases.json').read_text())
    # Instructions deliberately share three templates; source facts must be new.
    overlaps = [c['id'] for c in cases if digest(c['snapshot']['data']) in prior_facts]
    prompt_overlaps = [c['id'] for c in cases if digest(c['prompt']) in prior_prompts]
    if hits or overlaps or prompt_overlaps:
        raise ValueError('Prior exposure found; review before selecting a new pack')
    exposure = {'baselineCommit': baseline, 'auditedFiles': corpus,
                'priorPromptHashes': len(prior_prompts), 'priorFactHashes': len(prior_facts),
                'exactFactOverlaps': overlaps, 'exactInstructionOverlaps': prompt_overlaps,
                'sourceIdentifierHits': hits,
                'scope': 'All tracked research, benchmark and test files at baseline. New relative to local studies only; public model pretraining exposure is unknown. Earlier private pilot reused main-study tasks; its private archive is not published or scanned here.'}
    (PACK / 'exposure.json').write_text(json.dumps(exposure, indent=2) + '\n')
    result = audit()
    freeze = {'version': 'confirmation-v1', 'frozenAt': datetime.now(timezone.utc).isoformat(),
              'baselineCommit': baseline, 'files': frozen_files(), 'audit': result,
              'modelCallsBeforeFreeze': 0}
    (PACK / 'freeze.json').write_text(json.dumps(freeze, indent=2) + '\n')
    print(json.dumps({'freezeSha256': hashlib.sha256((PACK / 'freeze.json').read_bytes()).hexdigest(),
                      'audit': result}, indent=2))


if __name__ == '__main__':
    main()
