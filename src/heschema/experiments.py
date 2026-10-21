"""Controlled first-pass decoding and replayed repair studies, separate from schema richness."""

import copy
import random
from pathlib import Path

from .capabilities import capability_profile
from .context_schema import effective_schema, trusted_information
from .contracts import Contract, generation_envelope
from .failure_categories import VERSION as CATEGORY_VERSION
from .failure_categories import classify, relationship_checks
from .failure_categories import summary as category_summary
from .jsonio import canonical, digest, read_json, write_json
from .metrics import paired_effect
from .providers import Generation, content_has_reasoning_markers
from .repair import RepairLimits, coordinate, request_generation
from .repair_feedback import feedback_version
from .reports import provenance
from .rules import json_equal
from .schema import SchemaEngine
from .schema_projection import project_schema
from .study_evidence import VERSION as EVIDENCE_VERSION
from .study_evidence import StudyEvidence, append_jsonl, atomic_json
from .timing import VERSION as TIMING_VERSION
from .timing import summarize_timing
from .validation import validate_contract

MODES = ('prompt_only', 'native_original', 'native_projected')


def _task(case):
    contract = Contract(**case['contract'])
    snapshot = copy.deepcopy(case.get('context'))
    schema, evidence = effective_schema(contract, snapshot)
    original = generation_envelope(contract, contract.schema)
    effective = generation_envelope(contract, schema)
    projected, manifest = project_schema(original, effective)
    # This exact message list is used for every arm, including the projection factor.
    messages = [{'role': 'system', 'content': 'Return only whole JSON. Never execute tools. Authoritative schema: ' + canonical(effective) + '\nDeclared relationships: ' + canonical(contract.relationships) + '\nApproved bindings: ' + canonical(evidence['activeBindings']) + '\nTrusted facts: ' + canonical(trusted_information(snapshot))},
                {'role': 'user', 'content': case['prompt']}]
    return contract, snapshot, messages, effective, projected, manifest


def _score(evaluation, case):
    scored = copy.deepcopy(evaluation)
    intent = scored.get('semanticValid')
    if scored['stages']['json'] == 'valid' and 'expected' in case:
        actual, expected = scored['parsed'], case['expected']
        if case['contract'].get('outputKind') == 'tool_envelope' and isinstance(actual, dict):
            actual = {k: v for k, v in actual.items() if k != 'reason'}
            expected = {k: v for k, v in expected.items() if k != 'reason'}
        intent = json_equal(actual, expected)
    scored['intentAgreement'] = intent
    scored['success'] = bool(scored['accepted'] and intent is True)
    scored['intentEvidence'] = 'held_out_oracle' if 'expected' in case else scored['intentScope']
    return scored


def dry_run(cases, repeats=1, modes=MODES, warmup=0, repair_budgets=(), feedback_styles=('generic', 'raw', 'actionable')):
    if repeats < 1 or warmup < 0 or not modes or any(m not in MODES for m in modes):
        raise ValueError('Invalid experiment schedule')
    if any(not 0 <= n <= 5 for n in repair_budgets):
        raise ValueError('Repair budgets must be between zero and five')
    first = len(cases) * repeats * len(modes)
    repairs = first * len(feedback_styles) * sum(repair_budgets)
    return {'protocolVersion': 2, 'cases': len(cases), 'repeats': repeats, 'modes': list(modes),
            'firstPassRequests': first, 'warmupRequests': warmup,
            'maximumRepairRequests': repairs, 'maximumRequests': first + warmup + repairs,
            'notice': 'Upper bound only. No inference or provider initialization occurs in a dry run.'}


def _config(out, config):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    target = out / 'config.json'
    if target.exists() and read_json(target) != config:
        raise ValueError('Resume configuration differs; use a new output directory')
    write_json(target, config)
    return out


def _read_rows(out):
    rows = StudyEvidence(out).load_rows()
    latest = {(r['caseId'], r['repeat'], r['arm']): r for r in rows}
    return latest


def _attach_evidence(report, evidence):
    report['evidence'] = evidence.audit()
    report['designValid'] &= report['evidence']['evidenceComplete']
    report['comparisonValid'] &= report['evidence']['evidenceComplete']
    if not report['evidence']['evidenceComplete']:
        report['warnings'].append('Missing response/usage evidence limits the comparison; inspect evidence_report.json.')
    return report


def stage_summary(rows):
    n = len(rows)
    returned = [r for r in rows if r['firstEvaluation']['outputPresent']]
    accepted = [r for r in rows if r['status'] == 'ok']
    def measure(numerator, denominator):
        return {'numerator': numerator, 'denominator': denominator,
                'percent': numerator / denominator * 100 if denominator else None}
    stages = {}
    for key in ('json', 'originalSchema', 'context', 'relationships'):
        evaluated = [r for r in rows if r['firstEvaluation']['stages'][key] in {'valid', 'invalid'}]
        valid = sum(r['firstEvaluation']['stages'][key] == 'valid' for r in rows)
        stages[key] = {'amongAttempts': measure(valid, n), 'amongEvaluated': measure(valid, len(evaluated)),
                       'notEvaluated': n - len(evaluated)}
    failures = [r for r in rows if not r['firstPassSuccess']]
    attempts = [a for r in rows for a in r['attempts']]
    actual = [a for a in attempts if a.get('requestMade', True)]
    request_records = [entry for r in rows for entry in r['requestLedger'] if entry['requestMade']]
    usage_known = len(actual) == len(request_records)
    usage = {key: sum(a['generation'][key] for a in actual) if usage_known and actual and all(a['generation'][key] is not None for a in actual) else None for key in ('input_tokens', 'output_tokens')}
    timing = {}
    for status in sorted({r['status'] for r in rows}):
        durations = [r['latencyMs'] for r in rows if r['status'] == status]
        timing[status] = {'count': len(durations), 'totalMs': sum(durations), 'meanMs': sum(durations) / len(durations)}
    completions = {}
    for r in rows:
        generation = r['firstEvaluation'].get('generation') or {}
        status = generation.get('completion', 'not_evaluated') if r['attempts'] else 'not_evaluated'
        completions[status] = completions.get(status, 0) + 1
    final_stages = {}
    for key in ('json', 'originalSchema', 'context', 'relationships'):
        evaluations = [r.get('finalEvaluation') for r in rows]
        available = [e for e in evaluations if e is not None]
        evaluated = [e for e in available if e['stages'][key] in {'valid', 'invalid'}]
        valid = sum(e['stages'][key] == 'valid' for e in available)
        final_stages[key] = {'amongAttempts': measure(valid, n), 'amongEvaluated': measure(valid, len(evaluated)),
                             'notEvaluated': n - len(evaluated), 'missingFinalEvaluation': n - len(available)}
    return {'runs': n, 'requestAcceptance': measure(len(accepted), n), 'returnedFinalContent': measure(len(returned), n),
            'completionOutcomes': completions, 'stages': stages,
            'finalStages': final_stages,
            'firstFailureCategories': category_summary(rows), 'finalFailureCategories': category_summary(rows, final=True),
            'firstRelationshipChecks': relationship_checks(rows), 'finalRelationshipChecks': relationship_checks(rows, final=True),
            'schemaValidRelationshipRejected': measure(sum(r['firstEvaluation'].get('referenceSchemaValid') is True
                                                           and r['firstEvaluation']['stages']['relationships'] == 'invalid' for r in rows), n),
            'intentAgreement': measure(sum(r['firstEvaluation'].get('intentAgreement') is True for r in rows), sum(r['firstEvaluation'].get('intentAgreement') is not None for r in rows)),
            'firstPassSuccess': measure(sum(r['firstPassSuccess'] for r in rows), n),
            'finalSuccess': measure(sum(r['finalSuccess'] for r in rows), n),
            'recovery': measure(sum(r['finalSuccess'] for r in failures), len(failures)),
            'recoveryByAttemptCount': {str(k): measure(sum(r['finalSuccess'] and r['repairAttempts'] <= k for r in failures), len(failures)) for k in range(1, 6)},
            'actualRequests': sum(r['requestsAttempted'] for r in rows), 'usage': usage,
            'durationsByOutcome': timing,
            'timing': summarize_timing(rows),
            'totalValidationMs': sum(a['evaluation']['validationMs'] for a in attempts),
            'totalObservedModelMs': sum(a['generation']['latency_ms'] for a in actual),
            'legacyTimingNotice': 'totalObservedModelMs is a legacy adapter-latency sum, not isolated model inference time. Use timing for separated phases.'}


def _report(rows, config, scheduled, *, warmup_rows=None):
    models = sorted({a['generation']['model'] for r in rows for a in r['attempts'] if a['generation']['model']})
    confirmed = all(a['generation']['metadata'].get('resolvedModelConfirmed', False) for r in rows for a in r['attempts'])
    complete = len(rows) == scheduled
    empirical = config['provider'] != 'mock' and bool(models) and not any(a['generation']['metadata'].get('synthetic') for r in rows for a in r['attempts'])
    unexpected = any(r['status'] not in {'ok', 'native_request_rejected'} for r in rows)
    control_mismatches = []
    if config.get('thinkingRequested') is False:
        control_mismatches = [{'caseId': r['caseId'], 'repeat': r['repeat'], 'arm': r['arm']}
                              for r in rows if any(a['generation'].get('reasoning') or content_has_reasoning_markers(a['generation']['text'])
                                                   for a in r['attempts'])]
        control_mismatches += [{'warmupIndex': i} for i, recovery in enumerate(warmup_rows or [])
                               if any(a['generation'].get('reasoning') or content_has_reasoning_markers(a['generation']['text'])
                                      for a in recovery['attempts'])]
    warnings = ['Held-out fixtures are author-created synthetic cases, not evidence of company adoption.',
                'Request acceptance and passing outputs do not prove keyword enforcement.',
                'Timing includes the entire validation/IPC/repair path; no general latency or throughput claim.']
    if not empirical:
        warnings.append('MOCK/PIPELINE ONLY: no empirical inference conclusions.')
    if unexpected or not complete:
        warnings.append('Missing records or unexpected failures limit comparison.')
    if not confirmed or len(models) != 1:
        warnings.append('Resolved model identity is missing or changed.')
    if any(r['status'] == 'native_request_rejected' for r in rows):
        warnings.append('Native request rejection is a measured outcome; its exact cause and rejected-request model identity remain unknown.')
    if control_mismatches:
        warnings.append('Requested thinking=false conflicts with observed reasoning; fix the control before comparing decoding modes. Raw content was not stripped.')
    if config['study'] == 'repair_feedback':
        warnings.append('Pooled repair arms mix source decoding modes. Use bySourceMode to inspect recovery; failure categories overlap.')
    arms = sorted({r['arm'] for r in rows})
    effects = {}
    for arm in arms:
        baseline = 'prompt_only' if config['study'] == 'controlled_decoding' else arms[0]
        if arm != baseline:
            comparison = rows if config['study'] == 'controlled_decoding' else [{**r, 'firstPassSuccess': r['finalSuccess']} for r in rows]
            effects[arm] = paired_effect(comparison, baseline, arm)
    return {'protocolVersion': 2, 'study': config['study'], 'config': config, 'complete': complete,
            'completedRuns': len(rows), 'empiricalLLMEvidence': empirical,
            'designValid': bool(complete and not unexpected and confirmed and len(models) == 1 and not control_mismatches),
            'comparisonValid': bool(empirical and complete and not unexpected and confirmed and len(models) == 1 and not control_mismatches),
            'controlChecks': {'thinkingMismatchRows': control_mismatches,
                              'requestControlsRecorded': sum('requestControls' in a['generation'].get('metadata', {}) for r in rows for a in r['attempts']),
                              'contentExtraction': 'none; whole final content only'},
            'observedModels': models, 'arms': {arm: stage_summary([r for r in rows if r['arm'] == arm]) for arm in arms},
            'byFamily': {family: {arm: stage_summary([r for r in rows if r['arm'] == arm and r['cluster'] == family]) for arm in arms}
                         for family in sorted({r['cluster'] for r in rows})},
            'byCategory': {category: {arm: stage_summary([r for r in rows if r['arm'] == arm and r.get('caseMetadata', {}).get('category') == category]) for arm in arms}
                           for category in sorted({r['caseMetadata']['category'] for r in rows if r.get('caseMetadata', {}).get('category')})},
            'bySourceMode': {mode: {arm: stage_summary([r for r in rows if r['arm'] == arm and r['caseId'].endswith(':' + mode)]) for arm in arms}
                             for mode in MODES} if config['study'] == 'repair_feedback' else {},
            'effects': effects, 'warmup': warmup_rows or [], 'warnings': warnings}


async def run_decoding(cases, provider, out, *, repeats=1, modes=MODES, seed=42, max_tokens=1024,
                       temperature=0, max_requests=None, warmup=0, backend='jsonschema', cancel_event=None):
    if not cases or len({c['id'] for c in cases}) != len(cases):
        raise ValueError('Cases require unique IDs')
    schedule_info = dry_run(cases, repeats, modes, warmup)
    if provider.name != 'mock' and max_requests is None:
        raise ValueError('Live inference requires an explicit request budget')
    if max_tokens < 1 or (max_requests is not None and max_requests < 1):
        raise ValueError('Positive token and request budgets required')
    prepared = {c['id']: _task(c) for c in cases}
    config = {'protocolVersion': 2, 'study': 'controlled_decoding', 'datasetHash': digest(cases),
              'evidenceVersion': EVIDENCE_VERSION,
              'provider': provider.name, 'requestedModel': provider.model, 'repeats': repeats, 'modes': list(modes),
              'seed': seed, 'maxTokens': max_tokens, 'temperature': temperature, 'warmup': warmup, 'engine': backend,
              'repairs': 0, 'projectionVersion': '1', 'provenance': provenance(),
              'thinkingRequested': getattr(provider, 'thinking', None),
              'requestControls': provider.control_config() if hasattr(provider, 'control_config') else {},
              'failureCategoryVersion': CATEGORY_VERSION,
              'timingVersion': TIMING_VERSION,
              'scoringVersion': 'semantic_json_equality_v1',
              'requestInterval': provider.interval, 'caseIdentities': {c['id']: {'contract': prepared[c['id']][0].identity, 'contextHash': digest(c.get('context')), 'promptHash': digest(prepared[c['id']][2])} for c in cases}}
    if hasattr(provider, 'runtime_metadata'):
        config['provenance'].update(await provider.runtime_metadata())
    out = _config(out, config)
    evidence = StudyEvidence(out)
    latest = _read_rows(out)
    requests = 0
    unexpected_errors = 0
    engine = SchemaEngine(backend)
    warmup_path = out / 'warmup.json'
    warmup_evidence = StudyEvidence(out / 'warmup-evidence')
    warmup_evidence.set_schedule([{'warmupIndex': index} for index in range(warmup)])
    warmup_rows = [row['result'] for row in warmup_evidence.load_rows()]
    try:
        for index in range(len(warmup_rows), warmup):
            if max_requests is not None and requests >= max_requests:
                break
            c = cases[0]
            contract, snapshot, messages, _, _, _ = prepared[c['id']]
            session = warmup_evidence.session({'warmupIndex': index})
            async def request(messages, attempt):
                return await request_generation(provider, messages, seed, max_tokens, temperature)
            r = await coordinate(request, lambda g: validate_contract(g.text, engine, contract, snapshot, generation=g), messages,
                                 limits=RepairLimits(0, max_tokens=max_tokens), cancel_event=cancel_event, evidence=session)
            requests += r['requestsAttempted']
            session.commit({'result': r}, r)
            warmup_rows.append(r)
            atomic_json(warmup_path, warmup_rows)
        schedule = [(c, repeat, mode) for c in cases for repeat in range(repeats) for mode in modes]
        random.Random(seed).shuffle(schedule)
        evidence.set_schedule([{'caseId': c['id'], 'repeat': repeat, 'arm': mode} for c, repeat, mode in schedule])
        with (out / 'runs.jsonl').open('a', encoding='utf-8') as log:
            for order, (case, repeat, mode) in enumerate(schedule):
                key = case['id'], repeat, mode
                if key in latest and latest[key]['status'] in {'ok', 'native_request_rejected', 'unsupported_adapter'}:
                    continue
                if (cancel_event is not None and cancel_event.is_set()) or (max_requests is not None and requests >= max_requests):
                    break
                contract, snapshot, messages, effective, projected, manifest = prepared[case['id']]
                profile = capability_profile(provider.name, mode, model=provider.model)
                native = None if mode == 'prompt_only' else projected if mode == 'native_projected' else effective
                session = evidence.session({'caseId': case['id'], 'repeat': repeat, 'arm': mode})
                async def request(messages, attempt):
                    return await request_generation(provider, messages, seed + int(digest(case['id'])[:8], 16) + repeat, max_tokens, temperature, native)
                recovery = await coordinate(request, lambda g: validate_contract(g.text, engine, contract, snapshot, generation=g), messages,
                                            limits=RepairLimits(0, max_requests - requests if max_requests is not None else None, max_tokens), cancel_event=cancel_event,
                                            evidence=session)
                requests += recovery['requestsAttempted']
                first, final = _score(recovery['firstEvaluation'], case), _score(recovery['finalEvaluation'], case)
                status = 'ok' if recovery['attempts'] else 'native_request_rejected' if mode != 'prompt_only' and recovery['stopReason'] == 'request_rejected' else 'unsupported_adapter' if recovery['stopReason'] == 'unsupported_mode' else recovery['stopReason']
                row = {'caseId': case['id'], 'cluster': case.get('family', case['id']), 'repeat': repeat, 'arm': mode,
                       'status': status, 'modeOrder': order, 'promptHash': digest(messages), 'messages': messages,
                       'firstPassSuccess': first['success'], 'finalSuccess': final['success'], 'firstEvaluation': first, 'finalEvaluation': final,
                       'caseMetadata': {k: copy.deepcopy(case[k]) for k in ('category', 'classification', 'reviewStatus', 'sourceRefs') if k in case},
                       'firstObservations': classify(first, generation=recovery['attempts'][0]['generation'] if recovery['attempts'] else None, failure=recovery['failure']),
                       'finalObservations': classify(final, generation=recovery['attempts'][-1]['generation'] if recovery['attempts'] else None, failure=recovery['failure']),
                       'attempts': recovery['attempts'], 'requestLedger': recovery['requestLedger'], 'requestsAttempted': recovery['requestsAttempted'],
                       'repairAttempts': 0, 'latencyMs': recovery['elapsedMs'], 'timing': recovery['timing'],
                       'projection': manifest if mode == 'native_projected' else None,
                       'capability': profile, 'failure': recovery['failure'], 'provenance': case.get('provenance', 'author_created_synthetic')}
                row = session.commit(row, recovery)
                append_jsonl(log, row)
                latest[key] = row
                # Expected rejections do not trigger a transport outage breaker or silent fallback.
                unexpected_errors = unexpected_errors + 1 if status not in {'ok', 'native_request_rejected', 'unsupported_adapter'} else 0
                if unexpected_errors >= 3 or recovery['stopReason'] == 'cancelled':
                    break
        report = _report(list(latest.values()), config, schedule_info['firstPassRequests'], warmup_rows=warmup_rows)
        _attach_evidence(report, evidence)
        report['warmupEvidence'] = warmup_evidence.audit()
        report['designValid'] &= report['warmupEvidence']['evidenceComplete']
        report['comparisonValid'] &= report['warmupEvidence']['evidenceComplete']
        write_json(out / 'report.json', report)
        return report
    finally:
        evidence.audit()
        warmup_evidence.audit()
        engine.close()


async def run_repair_study(cases, provider, first_out, out, *, budgets=(1, 2), styles=('generic', 'raw', 'actionable'),
                           max_tokens=1024, max_requests=None, seed=42, temperature=0, backend='jsonschema', cancel_event=None):
    source = Path(first_out)
    source_config = read_json(source / 'config.json')
    if source_config.get('protocolVersion') != 2 or source_config.get('study') != 'controlled_decoding' or source_config['datasetHash'] != digest(cases):
        raise ValueError('Repair study requires compatible saved controlled first-pass evidence')
    current = provenance()
    if any(source_config['provenance'][key] != current[key] for key in ('codeHash', 'dependencies', 'pythonVersion')):
        raise ValueError('Repair code/dependencies must match saved first-pass evidence')
    if provider.name != source_config['provider'] or provider.model != source_config['requestedModel']:
        raise ValueError('Repair model/provider must match the saved first-pass experiment')
    controls = provider.control_config() if hasattr(provider, 'control_config') else {}
    if controls != source_config.get('requestControls', {}):
        raise ValueError('Repair request controls must match the saved first-pass experiment')
    if provider.name != 'mock' and max_requests is None:
        raise ValueError('Live inference requires an explicit request budget')
    if any(not 0 <= b <= 5 for b in budgets) or any(s not in {'generic', 'raw', 'actionable'} for s in styles) or not budgets or not styles:
        raise ValueError('Invalid repair experiment settings')
    if max_tokens != source_config['maxTokens'] or seed != source_config['seed'] or temperature != source_config['temperature'] or backend != source_config['engine']:
        raise ValueError('Repair sampling, limits and engine must match first-pass evidence')
    if source_config.get('evidenceVersion') != EVIDENCE_VERSION:
        raise ValueError('Saved first-pass evidence predates durable evidence; do not infer missing responses')
    saved = [r for r in _read_rows(source).values() if r['attempts']]
    config = {'protocolVersion': 2, 'study': 'repair_feedback', 'sourceHash': digest(saved), 'sourceConfigHash': digest(source_config),
              'evidenceVersion': EVIDENCE_VERSION,
              'datasetHash': digest(cases), 'provider': provider.name, 'requestedModel': provider.model,
              'budgets': list(budgets), 'styles': list(styles), 'maxTokens': max_tokens, 'seed': seed,
              'feedbackVersions': {style: feedback_version(style) for style in styles},
              'timingVersion': TIMING_VERSION,
              'temperature': temperature, 'engine': backend, 'provenance': provenance(),
              'thinkingRequested': source_config.get('thinkingRequested'), 'requestControls': controls,
              'failureCategoryVersion': CATEGORY_VERSION, 'scoringVersion': source_config.get('scoringVersion')}
    out = _config(out, config)
    evidence = StudyEvidence(out)
    latest = _read_rows(out)
    engine = SchemaEngine(backend)
    evidence.set_schedule([{'caseId': f"{row['caseId']}:{row['arm']}", 'repeat': row['repeat'], 'arm': f'{style}:{budget}'}
                           for row in saved for budget in budgets for style in styles])
    requests = 0
    try:
        by_id = {c['id']: c for c in cases}
        with (out / 'runs.jsonl').open('a', encoding='utf-8') as log:
            for source_row in saved:
                case = by_id[source_row['caseId']]
                contract, snapshot, messages, effective, projected, _ = _task(case)
                if digest(messages) != source_row['promptHash']:
                    raise ValueError('Saved first-pass prompt differs')
                for budget in budgets:
                    for style in styles:
                        source_id = f"{case['id']}:{source_row['arm']}"
                        arm = f'{style}:{budget}'
                        key = source_id, source_row['repeat'], arm
                        if key in latest and latest[key]['status'] == 'ok':
                            continue
                        if (cancel_event is not None and cancel_event.is_set()) or (max_requests is not None and requests >= max_requests):
                            continue
                        replay = Generation(**source_row['attempts'][0]['generation'])
                        native = None if source_row['arm'] == 'prompt_only' else projected if source_row['arm'] == 'native_projected' else effective
                        session = evidence.session({'caseId': source_id, 'repeat': source_row['repeat'], 'arm': arm})
                        async def request(messages, attempt):
                            return await request_generation(provider, messages, seed + int(digest(case['id'])[:8], 16) + source_row['repeat'], max_tokens, temperature, native)
                        recovery = await coordinate(request, lambda g: validate_contract(g.text, engine, contract, snapshot, generation=g), messages,
                                                    first_generation=replay, limits=RepairLimits(budget, max_requests - requests if max_requests is not None else None, max_tokens),
                                                    feedback_style=style, cancel_event=cancel_event, evidence=session)
                        requests += recovery['requestsAttempted']
                        first, final = _score(recovery['firstEvaluation'], case), _score(recovery['finalEvaluation'], case)
                        row = {'caseId': source_id, 'cluster': case.get('family', case['id']), 'repeat': source_row['repeat'], 'arm': arm,
                               'status': 'ok' if not recovery['failure'] else recovery['stopReason'], 'firstOutputHash': digest(replay.text),
                               'firstPassSuccess': first['success'], 'finalSuccess': final['success'], 'firstEvaluation': first, 'finalEvaluation': final,
                               'caseMetadata': source_row.get('caseMetadata', {}),
                               'firstObservations': classify(first, generation=recovery['attempts'][0]['generation'] if recovery['attempts'] else None, failure=recovery['failure'] if not recovery['attempts'] else None),
                               'finalObservations': classify(final, generation=recovery['attempts'][-1]['generation'] if recovery['attempts'] else None, failure=recovery['failure']),
                               'attempts': recovery['attempts'], 'requestLedger': recovery['requestLedger'], 'requestsAttempted': recovery['requestsAttempted'],
                               'repairAttempts': recovery['repairAttempts'], 'latencyMs': recovery['elapsedMs'], 'timing': recovery['timing'],
                               'stopReason': recovery['stopReason'], 'failure': recovery['failure'], 'provenance': source_row['provenance']}
                        row = session.commit(row, recovery)
                        append_jsonl(log, row)
                        latest[key] = row
        report = _report(list(latest.values()), config, len(saved) * len(budgets) * len(styles))
        _attach_evidence(report, evidence)
        report['sourceRequestsWithoutOutput'] = len(_read_rows(source)) - len(saved)
        write_json(out / 'report.json', report)
        return report
    finally:
        evidence.audit()
        engine.close()
