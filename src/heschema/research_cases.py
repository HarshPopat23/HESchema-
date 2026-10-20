"""Offline audits for prospective category cases and pinned public-source evidence."""

import copy
import hashlib
from collections import Counter
from pathlib import Path

from .experiments import _score, _task
from .failure_categories import classify
from .jsonio import digest, loads, read_json
from .schema import SchemaEngine
from .validation import validate_contract


def audit_cases(dataset, sources=None, *, backend='jsonschema'):
    dataset = Path(dataset)
    cases = [loads(line) for line in dataset.read_text(encoding='utf-8').splitlines() if line.strip()]
    failures, probes = [], []
    ids = [c['id'] for c in cases]
    if not cases or len(set(ids)) != len(ids):
        raise ValueError('Research cases require nonempty unique IDs')
    source_records = read_json(sources)['sources'] if sources else []
    source_ids = set()
    for source in source_records:
        if source['id'] in source_ids:
            raise ValueError('Public source IDs must be unique')
        source_ids.add(source['id'])
        if len(source['revision']) != 40 or any(c not in '0123456789abcdef' for c in source['revision']):
            raise ValueError('Public sources require a pinned commit')
        parent = Path(sources).resolve().parent
        for key in ('excerptPath', 'licensePath'):
            path = (parent / source[key]).resolve()
            if not path.is_relative_to(parent) or not path.is_file():
                raise ValueError('Public source evidence must be bundled inside the pack')
        path = parent / source['excerptPath']
        content_bytes = path.read_bytes().replace(b'\r\n', b'\n')
        if hashlib.sha256(content_bytes).hexdigest() != source['excerptSha256']:
            raise ValueError('Public source excerpt hash differs')
    engine = SchemaEngine(backend)
    try:
        for c in cases:
            required = {'family', 'category', 'classification', 'provenance', 'reviewStatus', 'publicationPermission', 'expected', 'counterexamples'}
            if required - c.keys():
                raise ValueError(f'{c["id"]}: missing research metadata')
            if c['reviewStatus'] not in {'unreviewed', 'independently_reviewed'}:
                raise ValueError('Unknown review status')
            if c['publicationPermission'] not in {'synthetic_example_only', 'granted_for_sanitized_example'}:
                raise ValueError('Withheld/unpermissioned examples cannot enter the published dataset')
            if set(c.get('sourceRefs', [])) - source_ids:
                raise ValueError('Unresolved public source reference')
            contract, snapshot, messages, *_ = _task(c)
            positive = _score(validate_contract(c['expected'], engine, contract, snapshot), c)
            if not positive['success']:
                failures.append({'caseId': c['id'], 'problem': 'Positive output is not accepted/task-correct'})
            changed = copy.deepcopy(c)
            changed['expected'] = {'scoring_only': 'never send this to a provider'}
            changed['counterexamples'] = []
            if _task(changed)[2] != messages:
                failures.append({'caseId': c['id'], 'problem': 'Scoring data leaked into generation messages'})
            if not c['counterexamples']:
                raise ValueError('Each prospective case needs a labelled negative control')
            for negative in c['counterexamples']:
                evaluation = _score(validate_contract(negative['output'], engine, contract, snapshot), c)
                stage = negative['expectedFailureStage']
                correct_stage = evaluation['accepted'] if stage == 'oracleOnly' else evaluation['stages'][stage] == 'invalid'
                matches = (correct_stage and evaluation['accepted'] is negative['expectedAccepted']
                           and evaluation['intentAgreement'] is negative['expectedIntentAgreement'])
                if not matches:
                    failures.append({'caseId': c['id'], 'probeId': negative['id'], 'problem': 'Negative control differs', 'stages': evaluation['stages']})
                probes.append({'caseId': c['id'], 'probeId': negative['id'], 'expectedStage': stage,
                               'matched': matches, 'observations': classify(evaluation),
                               'executionAuthorized': evaluation['executionAuthorized']})
    finally:
        engine.close()
    return {'auditType': 'prospective_category_case_audit', 'empiricalLLMEvidence': False,
            'engine': backend,
            'datasetHash': digest(cases), 'cases': len(cases), 'negativeControls': len(probes),
            'families': dict(Counter(c['family'] for c in cases)),
            'categories': dict(Counter(c['category'] for c in cases)),
            'reviewStatus': dict(Counter(c['reviewStatus'] for c in cases)),
            'publicSourceAdaptations': sum(bool(c.get('sourceRefs')) for c in cases),
            'publicSources': len(source_records), 'failures': failures, 'passed': not failures, 'probes': probes,
            'notice': 'Offline fixture verification only. Synthetic controls and public schema adaptations are not natural failures, company adoption or independently reviewed model evidence.'}
