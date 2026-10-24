"""Independent semantic oracle for the frozen H60 task pack; no runtime decisions reused."""
import argparse
import copy
import hashlib
import json
import math
from datetime import date
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'research/confirmation-60-v1'


def at(value, pointer):
    for token in pointer.split('/')[1:]:
        token = token.replace('~1', '/').replace('~0', '~')
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def equal(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    return a == b


def arithmetic(doc, rule):
    kind = rule['kind']
    if kind == 'count_equals':
        return len(at(doc, rule['arrayLocation']))
    if kind == 'sum_items_equals':
        return sum(at(item, rule['itemLocation']) for item in at(doc, rule['arrayLocation']))
    if kind == 'product_equals':
        return math.prod(at(doc, p) for p in rule['operands'])
    raise ValueError('Unsupported arithmetic in frozen pack')


def parse(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    def constant(_):
        raise ValueError('Non-finite JSON number')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def correct(raw, case, arm='A'):
    """Check all declared H60 semantics, accepting valid alternatives. D scores assembled output."""
    try:
        doc = parse(raw)
        definition = case['contract']
        schema = definition['schema']
        plan = case.get('d_calc') if arm == 'D' else None
        if plan:
            inputs = copy.deepcopy(schema)
            for rule in plan:
                key = rule['target'].removeprefix('/')
                if '/' in key:
                    raise ValueError('H60 calculation target must be top-level')
                inputs['properties'].pop(key)
                inputs['required'].remove(key)
            if not Draft202012Validator(inputs, format_checker=FormatChecker()).is_valid(doc):
                return False
            doc = copy.deepcopy(doc)
            for rule in plan:
                doc[rule['target'][1:]] = arithmetic(doc, rule)
        if not Draft202012Validator(schema, format_checker=FormatChecker()).is_valid(doc):
            return False
        context = case['snapshot']['data']
        for binding in definition['bindings']:
            actual = at(doc, binding['instanceLocation'])
            expected = at(context, binding['contextLocation'])
            keyword = binding.get('keyword', 'const')
            if keyword == 'const':
                valid = equal(actual, expected)
            elif keyword == 'enum':
                valid = any(equal(actual, x) for x in expected)
            else:
                raise ValueError('Unsupported binding in frozen H60 pack')
            if not valid:
                return False
        for rule in definition['relationships']:
            kind = rule['kind']
            if kind == 'date_before':
                valid = date.fromisoformat(at(doc, rule['left'])) < date.fromisoformat(at(doc, rule['right']))
            elif kind == 'equals':
                valid = equal(at(doc, rule['left']), at(doc, rule['right']))
            elif kind == 'reference_member':
                valid = any(equal(at(doc, rule['target']), x) for x in at(context, rule['contextLocation']))
            elif kind == 'unique_by':
                values = [at(x, rule['itemLocation']) for x in at(doc, rule['arrayLocation'])]
                valid = all(not equal(a, b) for i, a in enumerate(values) for b in values[i+1:])
            else:
                valid = equal(at(doc, rule['target']), arithmetic(doc, rule))
            if not valid:
                return False
        return True
    except (ValueError, TypeError, KeyError, IndexError, OverflowError):
        return False


def rescore():
    cases = {c['id']: c for c in json.loads((PACK / 'cases.json').read_text())}
    source = PACK / 'runs/runs.jsonl'
    rows = [json.loads(line) for line in source.read_text().splitlines()]
    out = {'sourceSha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'scope': 'offline rescore; not new inference', 'byArm': {}}
    for arm in 'ABCD':
        subset = [r for r in rows if r['arm'] == arm]
        first = final = false_accept = false_reject = 0
        for row in subset:
            case = cases[row['caseId']]
            initial = correct(row['rawResponse1'], case, arm)
            last = correct(row['rawResponse2'] if row['repairAttempted'] else row['rawResponse1'], case, arm)
            first += initial
            final += last
            false_accept += row['finalAccepted'] and not last
            false_reject += not row['finalAccepted'] and last
        out['byArm'][arm] = {'slots': len(subset), 'firstCorrect': first, 'finalCorrect': final, 'wrongAccepted': false_accept, 'correctRejected': false_reject}
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    path = PACK / 'independent-rescore.json'
    result = rescore()
    if args.check:
        assert json.loads(path.read_text()) == result
        print('RESCORE_VERIFIED')
    else:
        path.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
