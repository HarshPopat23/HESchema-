"""Capture public records once, then rebuild the confirmation pack without a network.

Only --capture uses the network (and the optional PyYAML capture dependency).
Never run --capture after starting a frozen experiment.
"""

import argparse
import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'research/confirmation-v1'


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def capture():
    import yaml  # Capture only: python -m pip install PyYAML

    sources = []
    client = httpx.Client(timeout=45, follow_redirects=True)

    def get(url):
        response = client.get(url)
        response.raise_for_status()
        return response.content

    def save(name, url, project, revision=None, decoder=json.loads):
        raw = get(url)
        path = 'sources/' + name
        (PACK / path).parent.mkdir(parents=True, exist_ok=True)
        (PACK / path).write_bytes(raw)
        sources.append({'id': name.split('.')[0], 'path': path, 'url': url,
                        'project': project, 'revision': revision,
                        'retrievedAt': datetime.now(timezone.utc).isoformat(),
                        'sha256': hashlib.sha256(raw).hexdigest()})
        return decoder(raw)

    def github(name, repo, branch, path, decoder=json.loads):
        revision = json.loads(get(f'https://api.github.com/repos/{repo}/commits/{branch}'))['sha']
        return save(name, f'https://raw.githubusercontent.com/{repo}/{revision}/{path}',
                    repo, revision, decoder)

    github('node.json', 'nodejs/Release', 'main', 'schedule.json')
    save('lifecycle.json', 'https://endoflife.date/api/python.json', 'endoflife-date/endoflife.date')
    github('spdx.json', 'spdx/license-list-data', 'main', 'json/licenses.json')
    save('media-types.csv', 'https://www.iana.org/assignments/media-types/application.csv',
         'IANA/media-types', decoder=lambda raw: raw)
    role = github('role.yaml', 'prometheus-operator/prometheus-operator', 'main',
                  'example/rbac/prometheus-operator/prometheus-operator-cluster-role.yaml', yaml.safe_load)
    write(PACK / 'sources/role-decoded.json', role)
    for formula in ('jq', 'git', 'curl', 'wget', 'ripgrep'):
        save(f'brew-{formula}.json', f'https://formulae.brew.sh/api/formula/{formula}.json', 'Homebrew/homebrew-core')
    write(PACK / 'sources.json', sources)
    client.close()


def build():
    from heschema.confirmation import make_case

    sources = json.loads((PACK / 'sources.json').read_text())
    by_id = {s['id']: s for s in sources}

    def load(key):
        return json.loads((PACK / by_id[key]['path']).read_text())

    cases = []

    def add(family, key, locator, facts):
        number = len(cases) + 1
        cases.append(make_case(f'confirmation-{number:02}', family, by_id[key]['project'],
                               key, locator, facts))

    node = load('node')
    for version in ('v16', 'v18', 'v20', 'v22', 'v24'):
        record = node[version]
        dates = sorted({v for k, v in record.items() if k in {'start', 'lts', 'maintenance', 'end'} and isinstance(v, str)})
        add('date_ordering', 'node', '/' + version,
            {'label': version, 'dates': dates})
    lifecycle = load('lifecycle')
    for cycle in ('3.9', '3.10', '3.11', '3.12', '3.13'):
        index, record = next((i, r) for i, r in enumerate(lifecycle) if r['cycle'] == cycle)
        dates = sorted({record[k] for k in ('releaseDate', 'support', 'eol') if isinstance(record.get(k), str)})
        add('date_ordering', 'lifecycle', '/' + str(index), {'label': cycle, 'dates': dates})
    licenses = load('spdx')['licenses']
    targets = ('MIT', 'Apache-2.0', 'BSD-2-Clause', 'MPL-2.0', 'ISC')
    selected = [next(r for r in licenses if r['licenseId'] == name) for name in targets]
    for target in selected:
        records = [{'identifier': r['licenseId'], 'name': r['name'], 'url': r['detailsUrl']} for r in selected]
        add('identifier_matching', 'spdx', '/licenses',
            {'requestedId': target['licenseId'], 'records': records})
    media = list(csv.DictReader(io.StringIO((PACK / by_id['media-types']['path']).read_text())))
    selected = [next(r for r in media if r['Name'] == name)
                for name in ('json', 'xml', 'pdf', 'zip', 'octet-stream')]
    for target in selected:
        records = [{'identifier': r['Name'], 'name': r['Template'],
                    'url': 'https://www.iana.org/assignments/media-types/' + r['Template']} for r in selected]
        add('identifier_matching', 'media-types', 'CSV rows keyed by Name',
            {'requestedId': target['Name'], 'records': records})
    role = json.loads((PACK / 'sources/role-decoded.json').read_text())
    # First five independent rule blocks, without wildcard interpretation.
    for index, rule in enumerate(role['rules'][:5]):
        add('list_membership', 'role', '/rules/' + str(index),
            {'label': 'apiGroups=' + json.dumps(rule['apiGroups']) + '; resources=' + json.dumps(rule['resources']),
             'allowed': rule['verbs']})
    for formula in ('jq', 'git', 'curl', 'wget', 'ripgrep'):
        record = load('brew-' + formula)
        add('list_membership', 'brew-' + formula, '/bottle/stable/files',
            {'label': record['full_name'], 'allowed': list(record['bottle']['stable']['files'])})
    # A different, deterministic order from source order avoids fixed first-answer positions.
    import random
    for case in cases:
        rng = random.Random(case['id'])
        facts = case['snapshot']['data']
        for key in ('dates', 'records', 'allowed'):
            if key in facts:
                rng.shuffle(facts[key])
    write(PACK / 'cases.json', cases)
    return cases


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', action='store_true')
    args = parser.parse_args()
    if args.capture:
        if (PACK / 'freeze.json').exists():
            raise ValueError('Cannot recapture a frozen pack; create a new study version')
        capture()
    print(f'Built {len(build())} cases from preserved public records.')
