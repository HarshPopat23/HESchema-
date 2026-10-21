"""Independent validity, source provenance and experiment-design checks."""

import asyncio
import copy
import json
import shutil
from pathlib import Path

import pytest

from heschema.confirmation import (
    PACK,
    audit,
    controls,
    messages,
    oracle,
    valid_outputs,
    verify_freeze,
)
from heschema.confirmation_run import run_slot, schedule, summarize
from heschema.jsonio import canonical
from heschema.providers import Generation, ProviderError

CASES = json.loads((PACK / 'cases.json').read_text())
PROTOCOL = json.loads((PACK / 'protocol.json').read_text())


def test_public_pack_and_exhaustive_controls():
    result = audit()
    sources = json.loads((PACK / 'sources.json').read_text())
    assert {p.name for p in (PACK / 'sources').iterdir()} == {
        Path(source['path']).name for source in sources} | {'role-decoded.json'}
    assert result == {'tasks': 30, 'clusters': 6, 'controls': 190,
                      'schemaOnlyAcceptedInvalidControls': 60}
    assert {c['family'] for c in CASES} == set(PROTOCOL['families'])
    assert all(sum(x['cluster'] == c['cluster'] for x in CASES) == 5 for c in CASES)
    assert '__not_in_' not in canonical([c['snapshot']['data'] for c in CASES])


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['id'])
def test_every_acceptable_alternative_and_corruption(case):
    for answer, expected in controls(case):
        assert oracle(case, answer) is expected
    assert not oracle(case, canonical(valid_outputs(case)[0]) + '\n{}')


def test_oracle_accepts_more_than_one_answer_per_choice_task():
    for family in ('date_ordering', 'list_membership'):
        case = next(c for c in CASES if c['family'] == family and len(valid_outputs(c)) > 1)
        assert all(oracle(case, output) for output in valid_outputs(case))


def test_same_prompt_and_rules_two_presentation_arms():
    for case in CASES:
        before = copy.deepcopy(case)
        full, compact = messages(case, 'full'), messages(case, 'compact')
        assert full[1] == compact[1] == {'role': 'user', 'content': case['prompt']}
        for result in (full, compact):
            assert canonical(case['contract']['relationships']) in result[0]['content']
            assert result[0]['content'].count('\nTrusted facts: ') == 1
        assert case == before
    with pytest.raises(ValueError):
        messages(CASES[0], 'schema_only')


def test_schedule_counts_pairing_and_repeat_seed():
    slots = schedule(CASES, PROTOCOL)
    assert len(slots) == 540
    assert slots == schedule(CASES, PROTOCOL)
    assert len({tuple(s.values()) for s in slots}) == 540
    for i in range(0, len(slots), 2):
        left, right = slots[i:i + 2]
        assert {left['arm'], right['arm']} == {'full', 'compact'}
        assert {k: v for k, v in left.items() if k != 'arm'} == {k: v for k, v in right.items() if k != 'arm'}
    assert {slots[i]['arm'] for i in range(0, len(slots), 2)} == {'full', 'compact'}


def test_projection_tampering_is_rejected(tmp_path):
    shutil.copytree(PACK, tmp_path / 'pack')
    path = tmp_path / 'pack/cases.json'
    cases = copy.deepcopy(CASES)
    cases[0]['snapshot']['data']['dates'].append('1900-01-01')
    path.write_text(json.dumps(cases))
    with pytest.raises(ValueError, match='projection mismatch'):
        audit(tmp_path / 'pack')


def test_source_snapshot_tampering_is_rejected(tmp_path):
    shutil.copytree(PACK, tmp_path / 'pack')
    (tmp_path / 'pack/sources/node.json').write_text('{}')
    with pytest.raises(ValueError, match='snapshot hash'):
        audit(tmp_path / 'pack')


def test_freeze_verifies_and_rejects_amendments(tmp_path):
    verify_freeze()
    shutil.copytree(PACK, tmp_path / 'pack')
    (tmp_path / 'pack/protocol.json').write_text('{}')
    with pytest.raises(ValueError, match='Frozen study changed'):
        verify_freeze(tmp_path / 'pack')


class Responses:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = []

    async def generate(self, messages, seed, max_tokens, temperature, retry=True):
        assert retry is False
        self.calls.append(copy.deepcopy(messages))
        response = next(self.outputs)
        if isinstance(response, Exception):
            raise response
        return Generation(canonical(response), input_tokens=50, output_tokens=10,
                          model='test-only', metadata={'finish_reason': 'stop'})


def slot(case=CASES[0], arm='full'):
    return {'caseId': case['id'], 'model': PROTOCOL['models'][0], 'repeat': 0, 'arm': arm}


def test_runtime_feedback_repairs_without_oracle(monkeypatch):
    case = CASES[0]
    bad = next(raw for raw, expected in controls(case) if not expected)
    provider = Responses([bad, valid_outputs(case)[-1]])
    import heschema.confirmation_run as runner
    original_oracle = runner.oracle

    def score_after_generation(*args):
        assert len(provider.calls) == 2
        return original_oracle(*args)

    monkeypatch.setattr(runner, 'oracle', score_after_generation)
    row = asyncio.run(run_slot(provider, case, slot(), PROTOCOL))
    assert row['complete'] and row['firstCorrect'] is False and row['finalCorrect'] is True
    assert row['result']['repairAttempts'] == 1
    feedback = provider.calls[1][-1]['content']
    assert 'date_before' in feedback and 'oracle' not in feedback.lower()


def test_resume_reuses_initial_generation_and_counts_prior_tokens():
    case = CASES[0]
    bad = next(raw for raw, expected in controls(case) if not expected)
    provider = Responses([bad, ProviderError('quota', status=429)])
    previous = asyncio.run(run_slot(provider, case, slot(), PROTOCOL))
    assert not previous['complete'] and previous['firstCorrect'] is False
    provider = Responses([valid_outputs(case)[0]])
    resumed = asyncio.run(run_slot(provider, case, slot(), PROTOCOL, previous))
    assert len(provider.calls) == 1 and len(provider.calls[0]) == 4
    assert resumed['result']['attempts'][0]['requestMade'] is False
    compact = asyncio.run(run_slot(Responses([valid_outputs(case)[0]]), case, slot(arm='compact'), PROTOCOL))
    report = summarize([previous, resumed, compact], [slot(), slot(arm='compact')])
    assert report['arms']['full']['totalTokensIncludingEarlierCheckpoints'] == 120
    assert report['providerRequestsAttempted'] == 4
    assert report['matchedPairs'] == 1


def test_incomplete_pairs_excluded_but_requests_preserved():
    case = CASES[0]
    row = asyncio.run(run_slot(Responses([valid_outputs(case)[0]]), case, slot(), PROTOCOL))
    report = summarize([row], [slot(), slot(arm='compact')])
    assert report['completedSlots'] == 1 and report['matchedPairs'] == 0
    assert report['providerRequestsAttempted'] == 1
    assert report['arms']['full']['matchedSlots'] == 0
