"""Offline replay of the resumed pilot; never calls models or edits historical answers."""

import argparse
import copy
import hashlib
import io
import json
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile

from jsonschema import Draft202012Validator, FormatChecker

from heschema.calculations import validate_with_calculations
from heschema.contracts import Contract
from heschema.diagnostics import resolve
from heschema.jsonio import canonical, loads
from heschema.rules import evaluate_rules, json_equal
from heschema.schema import SchemaEngine

ROOT = Path(__file__).resolve().parents[1]
DERIVED = {'WF': ['fileCount', 'totalSizeBytes'], 'PYPI': ['fileCount', 'totalSizeBytes'],
           'GBFS': ['stationCount', 'totalCapacity'], 'CR': ['listedAuthorCount'], 'USGS': []}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_lines(data):
    return [loads(line) for line in data.decode().splitlines() if line.strip()]


def verify_members(archive, files, prefix=''):
    for name, expected in files.items():
        if sha(archive.read(prefix + name)) != expected:
            raise ValueError('Archive member hash mismatch: ' + name)


def historical_replay(case, text, mode, effective, reference):
    """Independent reproduction of the frozen toolkit's five fixed adapters, not production policy."""
    try:
        document = loads(text)
        if not isinstance(document, dict):
            return False, False
        if mode == 'APP_CALC':
            prefix = case['original_case_id'].split('-')[0]
            core = copy.deepcopy(case['contract']['schema'])
            for key in DERIVED[prefix]:
                core['properties'].pop(key, None)
            core['required'] = [key for key in core['required'] if key not in DERIVED[prefix]]
            if not Draft202012Validator(core, format_checker=FormatChecker()).is_valid(document):
                return False, False
            if prefix in {'WF', 'PYPI'}:
                field = 'sizeInBytes' if prefix == 'WF' else 'size'
                document.update(fileCount=len(document['files']),
                                totalSizeBytes=sum(item[field] for item in document['files']))
            elif prefix == 'GBFS':
                document.update(stationCount=len(document['stations']),
                                totalCapacity=sum(item['capacity'] for item in document['stations']))
            elif prefix == 'CR':
                document['listedAuthorCount'] = len(document.get('authors', []))
        valid = Draft202012Validator(effective, format_checker=FormatChecker()).is_valid(document)
        valid = valid and evaluate_rules(document, case['contract']['relationships'])['status'] in {'valid', 'not_evaluated'}
        return bool(valid), json_equal(document, reference)
    except (ValueError, TypeError, KeyError, IndexError):
        return False, False


def syntax_probe(text):
    """Describe observed syntax only. No candidate editing or acceptance occurs here."""
    try:
        loads(text)
    except json.JSONDecodeError as error:
        return {'kind': 'trailing_content' if error.msg == 'Extra data' else 'syntax',
                'reason': error.msg, 'offset': error.pos, 'line': error.lineno, 'column': error.colno}
    except (ValueError, TypeError) as error:
        return {'kind': 'invalid_json_value', 'reason': str(error)}
    return None


def audit_archive(path):
    """Validate hashes and all saved phase scores, then extract the actual failing requests."""
    with ZipFile(path) as archive:
        manifest = loads(archive.read('ARCHIVE_MANIFEST.json'))
        verify_members(archive, manifest['files'])
        pack_bytes = archive.read('input_pack/HESchema_Real_Data_Pilot_30.zip')
        with ZipFile(io.BytesIO(pack_bytes)) as pack:
            prefix = 'HESchema_Real_Data_Pilot_30/'
            pack_manifest = loads(pack.read(prefix + 'MANIFEST.json'))
            verify_members(pack, pack_manifest['files'], prefix)
            cases = {case['id']: case for case in json_lines(pack.read(prefix + 'inputs/cases.jsonl'))}
            refs = {row['id']: row['expected_output'] for row in json_lines(
                pack.read(prefix + 'evaluation/references.jsonl'))}
            schemas = {key: loads(pack.read(prefix + c['effective_schema_file'])) for key, c in cases.items()}
            prompts = {mode: {r['id']: r['messages'] for r in json_lines(
                pack.read(prefix + 'messages/' + mode + '.jsonl'))}
                       for mode in ('FULL', 'COMPACT', 'APP_CALC')}
        rows = json_lines(archive.read('combined_run/judgments.jsonl'))
        requests = {r['call_id']: r for r in json_lines(archive.read('combined_run/requests.jsonl'))}
        responses = {r['call_id']: r for r in json_lines(archive.read('combined_run/responses.jsonl'))}
        if len({r['slot']['slot_id'] for r in rows}) != len(rows):
            raise ValueError('Duplicate verified slot')
        focused, recovered, discrepancies, provenance_issues = [], [], [], []
        successful_phases = 0
        prompts_verified = Counter()
        metrics, groups = defaultdict(Counter), defaultdict(dict)
        for row in rows:
            slot = row['slot']
            case = cases[slot['id']]
            metrics[slot['mode']]['results'] += 1
            metrics[slot['mode']]['first_correct'] += bool(row['first']['correct'])
            metrics[slot['mode']]['final_correct'] += bool(row['final']['correct'])
            groups[(slot['id'], slot['model'], slot['repeat'])][slot['mode']] = row
            failed = slot['mode'] == 'APP_CALC' and not row['final']['correct']
            tracked = slot['mode'] == 'APP_CALC' and not row['first']['correct']
            failure = {'slot': slot, 'source_group': case['source_group'],
                       'historical_final_correct': row['final']['correct'], 'phases': []}
            for phase, judgment in [('initial', 'first'), ('repair', 'after_repair')]:
                if phase not in row:
                    continue
                generation = row[phase]
                accepted, correct = historical_replay(case, generation.get('text') or '', slot['mode'],
                                                      schemas[slot['id']], refs[slot['id']])
                if generation.get('error'):
                    accepted = correct = False
                if (accepted, correct) != (row[judgment]['accepted'], row[judgment]['correct']):
                    discrepancies.append(slot['slot_id'] + ':' + phase)
                if generation.get('error'):
                    continue
                matches = [responses[call] for call in generation['calls']
                           if call in responses and responses[call]['http_status'] == 200]
                if len(matches) != 1:
                    provenance_issues.append(slot['slot_id'] + ':' + phase)
                    continue
                response = matches[0]
                request = requests[response['call_id']]
                raw = response['raw']
                choice = raw['choices'][0]
                if (raw['id'] != generation['provider_id']
                        or choice['message']['content'] != generation['text']
                        or choice['finish_reason'] != generation['finish_reason']
                        or request['slot_id'] != slot['slot_id'] or request['phase'] != phase):
                    provenance_issues.append(slot['slot_id'] + ':' + phase)
                messages = request['body']['messages']
                frozen = prompts[slot['mode']][slot['id']]
                if (messages[:len(frozen)] != frozen or
                        (phase == 'initial' and messages != frozen) or
                        (phase == 'repair' and messages[len(frozen)] != {
                            'role': 'assistant', 'content': row['initial']['text']})):
                    provenance_issues.append(slot['slot_id'] + ':' + phase + ':prompt')
                prompts_verified[phase] += 1
                successful_phases += 1
                if tracked:
                    failure['phases'].append({
                        'phase': phase, 'call_id': response['call_id'],
                        'request_body': request['body'], 'provider_response': raw,
                        'text_sha256': sha(generation['text'].encode()),
                    })
            if failed:
                focused.append(failure)
            elif tracked:
                recovered.append(failure)
        if discrepancies or provenance_issues:
            raise ValueError(f'Replay/provenance issues: {discrepancies}, {provenance_issues}')
        matched = [group for group in groups.values() if set(group) == {'FULL', 'COMPACT', 'APP_CALC'}]
        by_source, by_model = defaultdict(Counter), defaultdict(Counter)
        for group in matched:
            for mode, row in group.items():
                source = cases[row['slot']['id']]['source_group']
                by_source[source][mode + '_n'] += 1
                by_source[source][mode + '_correct'] += bool(row['final']['correct'])
                by_model[row['slot']['model']][mode + '_n'] += 1
                by_model[row['slot']['model']][mode + '_correct'] += bool(row['final']['correct'])
        selected = {row['slot']['id'] for row in [*focused, *recovered]}
        source_paths = {}
        for case_id in selected:
            expected = cases[case_id]['source']['raw_sha256']
            candidates = [p for p in (ROOT / 'research/contract-main-study-v1/sources').rglob('*.json')
                          if sha(p.read_bytes()) == expected]
            if len(candidates) != 1:
                raise ValueError('Cannot resolve preserved source snapshot for ' + case_id)
            source_paths[case_id] = str(candidates[0].relative_to(ROOT))
        return {
            'evidence_class': 'historical_public_source_model_responses',
            'live_model_requests': 0, 'source_archive_sha256': sha(Path(path).read_bytes()),
            'input_pack_sha256': sha(pack_bytes), 'archive_members_verified': len(manifest['files']),
            'input_pack_members_verified': len(pack_manifest['files']),
            'verified_results': len(rows), 'successful_phases_verified': successful_phases,
            'frozen_prompt_checks': dict(prompts_verified),
            'score_discrepancies': discrepancies, 'provenance_issues': provenance_issues,
            'all_available_metrics': {mode: dict(counts) for mode, counts in metrics.items()},
            'matched_blocks': len(matched),
            'matched_by_source': {source: dict(counts) for source, counts in by_source.items()},
            'matched_by_model': {model: dict(counts) for model, counts in by_model.items()},
            'cases': {key: {'input': cases[key], 'reference': refs[key],
                             'repository_source_snapshot': source_paths[key]} for key in sorted(selected)},
            'failures': focused,
            'recovered_source_failures': recovered,
        }


def replay_contract(bundle, case_id):
    definition = copy.deepcopy(bundle['cases'][case_id]['input']['contract'])
    definition['id'] = 'regression-' + case_id
    for rule in definition['relationships']:
        if rule['kind'] in {'count_equals', 'sum_items_equals'}:
            rule['compute'] = 'application'
    return Contract(**definition)


def punctuation_counterfactual(text):
    """Research-only minimal edits for these saved patterns; never used by runtime validation."""
    error = syntax_probe(text)
    if error and error['kind'] == 'trailing_content' and text[error['offset']:] == '}':
        return text[:-1], 'delete_one_trailing_closing_brace'
    if text.count(',"{"filename":') == 1:
        return text.replace(',"{"filename":', ',{"filename":', 1), 'delete_quote_before_record_object'
    if text.count('}},"filename":') == 1:
        return text.replace('}},"filename":', '}},{"filename":', 1), 'insert_record_opening_brace'
    return None, 'no_counterfactual_defined'


def replay_bundle(bundle, root=ROOT):
    """Replay extracted responses through current validation without accepting edited JSON."""
    summary = Counter()
    rows = []
    engine = SchemaEngine()
    try:
        for case in bundle['cases'].values():
            source_path = (root / case['repository_source_snapshot']).resolve()
            if not source_path.is_relative_to(root.resolve()):
                raise ValueError('Source snapshot must remain inside the repository')
            source = source_path.read_bytes()
            original = case['input']
            if sha(source) != original['source']['raw_sha256']:
                raise ValueError('Source hash mismatch')
            raw_source = loads(source)
            for target, location in original['source_field_map'].items():
                if not json_equal(resolve(original['context']['data'], target), resolve(raw_source, location)):
                    raise ValueError('Source mapping mismatch')
        for failure in bundle['failures']:
            case = bundle['cases'][failure['slot']['id']]
            contract = replay_contract(bundle, failure['slot']['id'])
            texts = []
            for phase in failure['phases']:
                raw = phase['provider_response']
                text = raw['choices'][0]['message']['content']
                if sha(text.encode()) != phase['text_sha256']:
                    raise ValueError('Response text hash mismatch')
                decision = validate_with_calculations(text, engine, contract, case['input']['context'])
                if decision['accepted'] or decision['calculation']['status'] != 'blocked':
                    raise ValueError('Malformed historical output was accepted or calculated')
                probe = syntax_probe(text)
                texts.append(text)
                rows.append({'slot_id': failure['slot']['slot_id'], 'phase': phase['phase'],
                             'text_sha256': phase['text_sha256'], 'syntax': probe,
                             'accepted': decision['accepted'],
                             'calculation_status': decision['calculation']['status']})
                summary[probe['kind']] += 1
                candidate, edit = punctuation_counterfactual(text)
                if candidate is not None:
                    # An offline counterfactual tests retained source values. It is not a
                    # recovered response and must not enter historical correctness totals.
                    result = validate_with_calculations(candidate, engine, contract, case['input']['context'])
                    matches = result['accepted'] and json_equal(result['parsed'], case['reference'])
                    rows[-1]['offline_counterfactual'] = {'edit': edit, 'matches_reference': matches,
                                                        'counted_as_recovery': False}
                    summary['counterfactual_matches'] += bool(matches)
            summary['identical_repairs'] += len(texts) == 2 and texts[0] == texts[1]
        recoveries = []
        for failure in bundle.get('recovered_source_failures', []):
            case = bundle['cases'][failure['slot']['id']]
            contract = replay_contract(bundle, failure['slot']['id'])
            for phase in failure['phases']:
                text = phase['provider_response']['choices'][0]['message']['content']
                if sha(text.encode()) != phase['text_sha256']:
                    raise ValueError('Response text hash mismatch')
                decision = validate_with_calculations(text, engine, contract, case['input']['context'])
                if decision['accepted'] != (phase['phase'] == 'repair'):
                    raise ValueError('Historical source failure/recovery did not replay')
                recoveries.append({'slot_id': failure['slot']['slot_id'], 'phase': phase['phase'],
                                   'accepted': decision['accepted'],
                                   'calculation_status': decision['calculation']['status']})
    finally:
        engine.close()
    return {'live_model_requests': 0, 'failed_slots_replayed': len(bundle['failures']),
            'counts': dict(summary), 'phases': rows, 'historical_source_recovery_phases': recoveries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--archive', type=Path)
    source.add_argument('--bundle', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    bundle = audit_archive(args.archive) if args.archive else loads(args.bundle.read_text())
    bundle = bundle.get('evidence', bundle)
    result = {'evidence': bundle, 'current_runtime_replay': replay_bundle(bundle)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(canonical({'output': str(args.out), 'replayed': len(bundle['failures']),
                     'model_requests': 0}))


if __name__ == '__main__':
    main()
