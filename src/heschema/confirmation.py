"""Prospective public-record confirmation: independent scoring, frozen inputs.

The oracle deliberately does not call HESchema validation, projection or rule code.
The runtime never receives oracle judgments or reference answers.
"""

import copy
import csv
import hashlib
import itertools
import json
from datetime import date
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from .context_schema import effective_schema
from .contract_prompt import contract_messages
from .contracts import Contract
from .jsonio import canonical, loads
from .schema import SchemaEngine
from .validation import validate_contract

PACK = Path(__file__).resolve().parents[2] / 'research/confirmation-v1'


def sha(path):
    p = Path(path)
    data = p.read_bytes()
    if p.name == 'media-types.csv':
        return hashlib.sha256(data).hexdigest()
    return hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest()


def make_case(identifier, family, project, source_id, locator, facts):
    """No generated source facts: callers must supply preserved-record projections."""
    string = {'type': 'string', 'minLength': 1}
    rules = []

    def member(target, context):
        rules.append({'id': 'member-' + target[1:], 'kind': 'reference_member',
                      'target': target, 'contextLocation': context})

    if family == 'date_ordering':
        properties = {'label': string, 'earlier': {**string, 'format': 'date'},
                      'later': {**string, 'format': 'date'}}
        anchor = 'label'
        member('/earlier', '/dates')
        member('/later', '/dates')
        rules.append({'id': 'ordered', 'kind': 'date_before', 'left': '/earlier', 'right': '/later'})
        prompt = ('Prepare a release-lifecycle interval using only this record. Return its label '
                  'and any two distinct listed dates as earlier and later, with earlier strictly before later. '
                  'More than one interval may be correct. Do not invent or change dates.')
    elif family == 'identifier_matching':
        record = {'type': 'object', 'properties': {key: string for key in ('identifier', 'name', 'url')},
                  'required': ['identifier', 'name', 'url'], 'additionalProperties': False}
        properties = {'requestedId': string, 'selected': record}
        anchor = 'requestedId'
        member('/selected', '/records')
        rules.append({'id': 'identifier-match', 'kind': 'equals',
                      'left': '/requestedId', 'right': '/selected/identifier'})
        prompt = ('Resolve the exact, case-sensitive requestedId in the supplied registry candidates. '
                  'Return requestedId and the complete matching record as selected. Preserve its identifier, '
                  'name and URL exactly; do not mix fields from different records.')
    elif family == 'list_membership':
        properties = {'label': string, 'choice': string}
        anchor = 'label'
        member('/choice', '/allowed')
        prompt = ('Choose any one explicitly listed allowed value for this exact label. Return label and choice. '
                  'For an RBAC rule this means a verb allowed by that rule block; for a Homebrew formula '
                  'it means an available bottle platform tag. Treat strings literally, without expanding wildcards. '
                  'Multiple choices may be correct; do not invent a value.')
    else:
        raise ValueError('Unknown confirmation family')
    schema = {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}
    contract = Contract(id=identifier, version='1', schema=schema,
                        bindings=[{'instanceLocation': '/' + anchor, 'contextLocation': '/' + anchor}],
                        relationships=rules)
    return {'id': identifier, 'family': family, 'cluster': project, 'sourceId': source_id,
            'sourceLocator': locator, 'provenance': 'researcher_adaptation_of_public_record',
            'prompt': prompt, 'contract': contract.as_dict(),
            'snapshot': {'id': identifier + '-source', 'version': 1, 'confirmed': True,
                         'approvedPointers': ['/' + key for key in facts], 'data': facts, 'facts': []}}


def oracle(case, raw):
    """All valid alternatives, not equality with one preferred answer."""
    try:
        document = loads(raw) if isinstance(raw, str) else loads(canonical(raw))
        validator = Draft202012Validator(case['contract']['schema'], format_checker=FormatChecker())
        if not validator.is_valid(document):
            return False
        facts = case['snapshot']['data']
        family = case['family']
        if family == 'date_ordering':
            return (document['label'] == facts['label']
                    and document['earlier'] in facts['dates'] and document['later'] in facts['dates']
                    and date.fromisoformat(document['earlier']) < date.fromisoformat(document['later']))
        if family == 'identifier_matching':
            return (document['requestedId'] == facts['requestedId']
                    and document['selected'] in facts['records']
                    and document['selected']['identifier'] == facts['requestedId'])
        if family == 'list_membership':
            return document['label'] == facts['label'] and document['choice'] in facts['allowed']
    except (ValueError, TypeError, KeyError):
        return False
    raise ValueError('Unknown confirmation family')


def valid_outputs(case):
    facts = case['snapshot']['data']
    if case['family'] == 'date_ordering':
        return [{'label': facts['label'], 'earlier': a, 'later': b}
                for a, b in itertools.permutations(facts['dates'], 2) if date.fromisoformat(a) < date.fromisoformat(b)]
    if case['family'] == 'identifier_matching':
        return [{'requestedId': facts['requestedId'], 'selected': r} for r in facts['records']
                if r['identifier'] == facts['requestedId']]
    return [{'label': facts['label'], 'choice': value} for value in facts['allowed']]


def controls(case):
    """Deliberately corrupted controls are synthetic probes, never live study inputs."""
    correct = valid_outputs(case)
    bad = copy.deepcopy(correct[0])
    if case['family'] == 'date_ordering':
        bad['earlier'], bad['later'] = bad['later'], bad['earlier']
    elif case['family'] == 'identifier_matching':
        bad['selected'] = next(r for r in case['snapshot']['data']['records']
                               if r['identifier'] != bad['requestedId'])
    else:
        bad['choice'] = '__not_in_the_preserved_allowed_list__'
    wrong_source = copy.deepcopy(correct[0])
    wrong_source[next(iter(wrong_source))] = '__wrong_source__'
    return [(answer, True) for answer in correct] + [(bad, False), (wrong_source, False), ('{', False)]


def messages(case, arm):
    if arm not in {'full', 'compact'}:
        raise ValueError('Unknown confirmation arm')
    contract = Contract(**case['contract'])
    projected, evidence = effective_schema(contract, case['snapshot'])
    schema = projected if arm == 'full' else contract.schema
    return contract_messages(contract, case['snapshot'], evidence, schema, case['prompt'], style=arm)


def audit(pack=PACK):
    """Offline source/case/control audit; network and model access are unnecessary."""
    pack = Path(pack)
    cases = json.loads((pack / 'cases.json').read_text())
    sources = json.loads((pack / 'sources.json').read_text())
    for source in sources:
        if sha(pack / source['path']) != source['sha256']:
            raise ValueError('Source snapshot hash mismatch: ' + source['id'])
    check_source_projections(cases, sources, pack)
    engine = SchemaEngine()
    checked = schema_only_misses = 0
    for case in cases:
        contract = Contract(**case['contract'])
        for raw, expected in controls(case):
            observed = oracle(case, raw)
            result = validate_contract(raw, engine, contract, case['snapshot'])
            if observed != expected or result['accepted'] != expected:
                raise ValueError('Control disagreement: ' + case['id'])
            schema_only_misses += bool(not expected and result['referenceSchemaValid'])
            checked += 1
        if not valid_outputs(case):
            raise ValueError('No valid answer: ' + case['id'])
    if len(cases) != 30 or len({c['cluster'] for c in cases}) != 6:
        raise ValueError('Expected 30 tasks and six source clusters')
    return {'tasks': len(cases), 'clusters': 6, 'controls': checked,
            'schemaOnlyAcceptedInvalidControls': schema_only_misses}


def check_source_projections(cases, sources, pack):
    """Re-read raw records independently of the case builder; fail on invented facts."""
    import yaml  # Research preflight dependency, not used by the application.

    raw = {s['id']: (pack / s['path']).read_text() for s in sources}
    role = yaml.safe_load(raw['role'])
    if role != json.loads((pack / 'sources/role-decoded.json').read_text()):
        raise ValueError('YAML decoding mismatch')
    for case in cases:
        key, facts = case['sourceId'], case['snapshot']['data']
        if key in {'node', 'lifecycle'}:
            document = json.loads(raw[key])
            token = case['sourceLocator'][1:]
            record = document[token] if key == 'node' else document[int(token)]
            fields = ('start', 'lts', 'maintenance', 'end') if key == 'node' else ('releaseDate', 'support', 'eol')
            expected = {record[k] for k in fields if isinstance(record.get(k), str)}
            label = token if key == 'node' else record['cycle']
            valid = set(facts['dates']) == expected and facts['label'] == label
        elif key in {'spdx', 'media-types'}:
            if key == 'spdx':
                entries = {r['licenseId']: {'identifier': r['licenseId'], 'name': r['name'], 'url': r['detailsUrl']}
                           for r in json.loads(raw[key])['licenses']}
            else:
                entries = {r['Name']: {'identifier': r['Name'], 'name': r['Template'],
                                       'url': 'https://www.iana.org/assignments/media-types/' + r['Template']}
                           for r in csv.DictReader(raw[key].splitlines())}
            valid = (facts['requestedId'] in entries and len(facts['records']) == 5
                     and all(r == entries.get(r['identifier']) for r in facts['records']))
        elif key == 'role':
            rule = role['rules'][int(case['sourceLocator'].rsplit('/', 1)[1])]
            label = 'apiGroups=' + json.dumps(rule['apiGroups']) + '; resources=' + json.dumps(rule['resources'])
            valid = facts['label'] == label and set(facts['allowed']) == set(rule['verbs'])
        elif key.startswith('brew-'):
            record = json.loads(raw[key])
            valid = (facts['label'] == record['full_name']
                     and set(facts['allowed']) == set(record['bottle']['stable']['files']))
        else:
            raise ValueError('Unknown source projection')
        if not valid:
            raise ValueError('Public record projection mismatch: ' + case['id'])


def frozen_files(pack=PACK):
    paths = ['cases.json', 'sources.json', 'protocol.json', 'exposure.json']
    sources = json.loads((pack / 'sources.json').read_text())
    paths.extend(s['path'] for s in sources)
    paths.append('sources/role-decoded.json')
    return {path: sha(Path(pack) / path) for path in sorted(paths)}


def verify_freeze(pack=PACK):
    pack = Path(pack)
    manifest = json.loads((pack / 'freeze.json').read_text())
    if manifest['files'] != frozen_files(pack):
        raise ValueError('Frozen study changed; create a new version, never overwrite a started study')
    return manifest
