"""Task-specific conventional application checks for offline counterfactual replay.

Written from the six H60 task families and source facts, without evaluating
contract bindings/relationships or reusing the independent oracle.
"""
import copy
from datetime import date

from jsonschema import Draft202012Validator, FormatChecker

from heschema.jsonio import loads


def conventional(raw, case, arm='A'):
    try:
        doc = loads(raw)
        facts = case['snapshot']['data']
        schema = copy.deepcopy(case['contract']['schema'])
        family = case['family']
        assembled = arm == 'D' and bool(case.get('d_calc'))
        if assembled:
            target = 'count' if family == 'Counts' else 'total'
            schema['properties'].pop(target)
            schema['required'].remove(target)
        if not Draft202012Validator(schema, format_checker=FormatChecker()).is_valid(doc):
            return False
        if family == 'Date ordering':
            return (doc['start'] in facts['dates'] and doc['end'] in facts['dates']
                    and date.fromisoformat(doc['start']) < date.fromisoformat(doc['end']))
        if family == 'Identifier matching':
            records = [r for r in facts['candidates'] if r['id'] == facts['requestedId']]
            return doc['requestedId'] == facts['requestedId'] and doc['record'] in records
        if family == 'List membership':
            return doc['selected'] in facts['allowed']
        if family == 'Uniqueness':
            ids = [r['id'] for r in doc['records']]
            return len(set(ids)) == len(ids) and all(i in facts['allowedIds'] for i in ids)
        if family == 'Counts':
            expected = len(facts['items'])
        elif family == 'Sums / products':
            expected = (facts['copies'] * facts['perCopy'] if 'copies' in facts
                        else sum(row['amount'] for row in facts['rows']))
        else:
            raise ValueError('Unknown H60 family')
        if not all(doc[k] == v for k, v in facts.items()):
            return False
        if assembled:
            doc[target] = expected
        if not Draft202012Validator(case['contract']['schema'], format_checker=FormatChecker()).is_valid(doc):
            return False
        return doc['count' if family == 'Counts' else 'total'] == expected
    except (ValueError, TypeError, KeyError, IndexError, OverflowError):
        return False
