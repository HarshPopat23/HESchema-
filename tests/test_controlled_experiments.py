import asyncio
import copy

import pytest

from heschema.experiments import dry_run, run_decoding, run_repair_study
from heschema.jsonio import canonical, loads
from heschema.providers import Generation, ProviderError
from heschema.reports import adapt_report

CASE = {'id': 'private-case', 'family': 'family', 'provenance': 'author_created_synthetic_heldout',
        'contract': {'id': 'n', 'version': '1', 'schema': {'type': 'object', 'properties': {'n': {'type': 'integer'}}, 'required': ['n']}},
        'prompt': 'Return the requested n.', 'expected': {'n': 928173}}


class Fake:
    name, model, interval = 'mock', 'test-stub', 0
    def __init__(self):
        self.seen = []
        self.valid = False
    async def generate(self, messages, *args, **kwargs):
        self.seen.append((copy.deepcopy(messages), kwargs))
        # The test's fake knows its output. HESchema must never put this gold value in feedback.
        return Generation(canonical({'n': 928173} if self.valid else {'n': 'wrong'}), 5, 10, self.model,
                          metadata={'finish_reason': 'stop', 'resolvedModelConfirmed': True, 'synthetic': True})


def test_identical_prompt_hashes_no_gold_leakage_resume_and_dry_run(tmp_path):
    async def check():
        p = Fake()
        report = await run_decoding([CASE], p, tmp_path, max_tokens=20)
        assert report['complete'] and not report['empiricalLLMEvidence']
        rows = [loads(s) for s in (tmp_path / 'runs.jsonl').read_text().splitlines()]
        assert len({r['promptHash'] for r in rows}) == 1
        assert all('928173' not in canonical(messages) for messages, _ in p.seen)
        assert all(kwargs['retry'] is False for _, kwargs in p.seen)
        assert sum('format_schema' in k for _, k in p.seen) == 2
        await run_decoding([CASE], p, tmp_path, max_tokens=20)
        assert len(p.seen) == 3
        with pytest.raises(ValueError, match='Resume'):
            await run_decoding([CASE], p, tmp_path, max_tokens=21)
    asyncio.run(check())
    assert dry_run([CASE], repeats=2, warmup=1, repair_budgets=[1, 2])['maximumRequests'] == 61


def test_repair_comparison_replays_identical_first_output_and_counts_only_new_calls(tmp_path):
    async def check():
        p = Fake()
        first, repaired = tmp_path / 'first', tmp_path / 'repairs'
        await run_decoding([CASE], p, first, max_tokens=20)
        p.valid = True
        report = await run_repair_study([CASE], p, first, repaired, budgets=[1], max_tokens=20)
        assert report['complete'] and not report['empiricalLLMEvidence']
        rows = [loads(s) for s in (repaired / 'runs.jsonl').read_text().splitlines()]
        assert len(rows) == 9 and len({r['firstOutputHash'] for r in rows}) == 1
        assert all(r['requestsAttempted'] == 1 and r['finalSuccess'] for r in rows)
        assert all(a['usage']['output_tokens'] == 30 for a in report['arms'].values())
        assert all('928173' not in canonical(messages) for messages, _ in p.seen)
    asyncio.run(check())


def test_expected_native_rejections_are_measured_complete_outcomes(tmp_path):
    class Rejecting(Fake):
        name = 'ollama'
        async def generate(self, messages, *args, **kwargs):
            if kwargs.get('format_schema') is not None:
                raise ProviderError('HTTP 400', code='request_rejected', status=400)
            self.valid = True
            return await super().generate(messages, *args, **kwargs)
    r = asyncio.run(run_decoding([CASE], Rejecting(), tmp_path, max_requests=3))
    assert r['complete'] and r['designValid'] and not r['comparisonValid']
    native = r['arms']['native_original']
    assert native['requestAcceptance'] == {'numerator': 0, 'denominator': 1, 'percent': 0}
    assert native['stages']['originalSchema']['amongEvaluated']['denominator'] == 0
    assert native['durationsByOutcome']['native_request_rejected']['count'] == 1


def test_legacy_adapter_does_not_rewrite_evidence():
    old = {'config': {'provider': 'ollama'}, 'arms': {'old': {'schemaValid': True}}}
    adapted = adapt_report(old)
    assert adapted['sourceProtocolVersion'] == 'legacy_unknown'
    assert not adapted['legacyAdapter']['inferredEvidence']
    assert 'legacyAdapter' not in old and adapted['arms'] == old['arms']
