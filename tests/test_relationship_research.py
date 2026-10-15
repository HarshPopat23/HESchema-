import json
import shutil

import pytest

from heschema.contracts import Contract
from heschema.experiments import _score
from heschema.failure_categories import classify
from heschema.providers import ROOT
from heschema.repair import feedback_message
from heschema.research_cases import audit_cases
from heschema.rules import check_rules, evaluate_rules
from heschema.schema import SchemaEngine
from heschema.validation import validate_contract


@pytest.mark.parametrize('rule,good,bad', [
    ({'id': 'm', 'kind': 'member_of', 'target': '/selected', 'arrayLocation': '/choices'},
     {'choices': [1], 'selected': 1.0}, {'choices': [1], 'selected': True}),
    ({'id': 'c', 'kind': 'count_equals', 'target': '/count', 'arrayLocation': '/items'},
     {'items': [], 'count': 0.0}, {'items': [], 'count': False}),
    ({'id': 's', 'kind': 'sum_items_equals', 'target': '/total', 'arrayLocation': '/items', 'itemLocation': '/a~1b'},
     {'items': [{'a/b': 10**100}, {'a/b': -1}], 'total': 10**100 - 1},
     {'items': [{'a/b': 1.5}], 'total': 1}),
    ({'id': 'u', 'kind': 'unique_by', 'arrayLocation': '/items', 'itemLocation': '/id'},
     {'items': [{'id': True}, {'id': 1}]}, {'items': [{'id': 1, 'name': 'a'}, {'id': 1.0, 'name': 'b'}]}),
])
def test_collection_rules_use_semantic_json_equality_and_exact_integer_arithmetic(rule, good, bad):
    check_rules([rule])
    assert evaluate_rules(good, [rule])['status'] == 'valid'
    result = evaluate_rules(bad, [rule])
    assert result['status'] == 'invalid'
    assert result['errors'][0]['kind'] == rule['kind']
    assert result['rules'][0]['ruleId'] == rule['id']


@pytest.mark.parametrize('kind', ['count_equals', 'sum_items_equals', 'member_of', 'unique_by'])
def test_collection_rule_missing_wrong_type_and_empty_array(kind):
    rule = {'id': 'rule', 'kind': kind, 'arrayLocation': '/items'}
    if kind != 'unique_by':
        rule['target'] = '/total'
    if kind in {'sum_items_equals', 'unique_by'}:
        rule['itemLocation'] = ''
    check_rules([rule])
    assert evaluate_rules({'items': {}}, [rule])['status'] == 'invalid'
    assert evaluate_rules({}, [rule])['status'] == 'needs_context'
    expected = 'invalid' if kind == 'member_of' else 'valid'
    assert evaluate_rules({'items': [], 'total': 0}, [rule])['status'] == expected


@pytest.mark.parametrize('rules', [None, ['not-an-object'], [{'kind': 'equals', 'id': 'x'}],
                                  [{'kind': 'count_equals', 'id': 'x', 'target': '/x', 'arrayLocation': '/a', 'expression': 'code'}],
                                  [{'kind': [], 'id': 'x'}], [{'kind': 'equals', 'id': [], 'left': '', 'right': ''}]])
def test_invalid_relationship_configuration_fails_at_registration(rules):
    with pytest.raises(ValueError):
        Contract('bad', '1', {}, relationships=rules)


def test_relationship_feedback_identifies_protected_operands_and_context_still_rejects_changes():
    contract = Contract('invoice', '1', {'type': 'object'},
                        bindings=[{'instanceLocation': '/tax', 'contextLocation': '/tax'}],
                        relationships=[{'id': 'total', 'kind': 'sum_equals', 'operands': ['/base', '/tax'], 'target': '/total'}])
    context = {'id': 'source', 'version': 1, 'confirmed': True, 'data': {'tax': 167}, 'approvedPointers': ['/tax'], 'facts': []}
    engine = SchemaEngine()
    try:
        bad = validate_contract({'base': 3333, 'tax': 167, 'total': 3333}, engine, contract, context)
        assert bad['errors'][0]['protectedInputs'] == ['/tax']
        feedback = json.loads(feedback_message(bad['errors']).split(': ', 1)[1])
        assert feedback[0]['protectedInputs'] == ['/tax']
        assert feedback[0]['inputLocations'] == ['/total', '/base', '/tax']
        changed = validate_contract({'base': 3333, 'tax': 1, 'total': 3334}, engine, contract, context)
        assert changed['stages']['context'] == 'invalid'
        assert not changed['accepted']
    finally:
        engine.close()


def test_failure_categories_separate_evidence_from_keyword_support_and_source_truth():
    case = {'contract': {'schema': {}}, 'expected': {'n': 1}}
    engine = SchemaEngine()
    try:
        c = Contract('number', '1', {})
        scored = _score(validate_contract({'n': 2}, engine, c), case)
    finally:
        engine.close()
    labels = classify(scored)
    assert labels['categories'] == ['runtime_accepted_oracle_mismatch']
    context_error = {'errors': [{'code': 'CONTEXT_MISMATCH', 'details': [{'code': 'SCHEMA_INVALID', 'keyword': 'const'}]}]}
    labels = classify(context_error)
    assert labels['categories'] == ['trusted_context_mismatch']
    assert labels['schemaKeywords'] == ['const']
    rejected = classify({}, failure={'code': 'request_rejected', 'httpStatus': 400})
    assert rejected['categories'] == ['provider_request_rejected']
    assert rejected['unsupportedKeywordInference'] is False


def test_prospective_pack_has_positive_negative_controls_and_honest_provenance():
    pack = ROOT / 'research/relationship-categories-v1'
    result = audit_cases(pack / 'cases.jsonl', pack / 'sources.json')
    assert result['passed'] and not result['empiricalLLMEvidence']
    assert result['cases'] == result['negativeControls'] == 86
    assert result['publicSourceAdaptations'] == 6 and result['publicSources'] == 2
    assert result['reviewStatus'] == {'unreviewed': 86}
    assert all(not p['executionAuthorized'] for p in result['probes'])


def test_published_pack_rejects_withheld_evidence_and_changed_source_excerpts(tmp_path):
    pack = ROOT / 'research/relationship-categories-v1'
    case = json.loads((pack / 'cases.jsonl').read_text().splitlines()[0])
    case['publicationPermission'] = 'withheld'
    path = tmp_path / 'cases.jsonl'
    path.write_text(json.dumps(case) + '\n')
    with pytest.raises(ValueError, match='Withheld'):
        audit_cases(path)
    source = json.loads((pack / 'sources.json').read_text())
    source['sources'][0]['excerptSha256'] = 'incorrect'
    # The excerpt must stay inside the pinned pack; do not follow filesystem escapes.
    source['sources'][0]['excerptPath'] = '../outside.ts'
    sources = tmp_path / 'sources.json'
    sources.write_text(json.dumps(source))
    with pytest.raises(ValueError, match='inside the pack'):
        audit_cases(path, sources)
    copied = tmp_path / 'copied'
    shutil.copytree(pack, copied)
    source = json.loads((copied / 'sources.json').read_text())
    source['sources'][0]['excerptSha256'] = 'incorrect'
    (copied / 'sources.json').write_text(json.dumps(source))
    with pytest.raises(ValueError, match='excerpt hash'):
        audit_cases(copied / 'cases.jsonl', copied / 'sources.json')
