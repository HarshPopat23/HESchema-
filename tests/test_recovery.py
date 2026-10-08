import asyncio

import pytest

from heschema.benchmark import run
from heschema.dataset import generate_cases
from heschema.jsonio import canonical
from heschema.providers import Generation, ProviderError
from heschema.schema import SchemaEngine
from heschema.validation import envelope, evaluate


def test_json_null_is_valid_json_but_invalid_envelope():
    result = evaluate("null", SchemaEngine(), {}, {}, envelope("refuse"))
    assert result["jsonValid"] and not result["success"]


def test_provider_error_resume_deduplicates_reports_but_keeps_history(tmp_path):
    class Fake:
        name, model, interval = "mock", "recovery-stub", 0
        failing = True
        async def generate(self, *args):
            if self.failing:
                raise ProviderError("Temporary outage")
            return Generation(canonical(envelope("refuse")), 0, 0, self.model)
    async def check():
        provider = Fake()
        cases = generate_cases()[-1:]
        failed = await run(cases, provider, tmp_path, repeats=1, repairs=0)
        assert failed["completedRuns"] == 3
        assert not failed["comparisonValid"]
        provider.failing = False
        recovered = await run(cases, provider, tmp_path, repeats=1, repairs=0)
        assert recovered["completedRuns"] == 3
        assert all(arm["firstPassSuccessPercent"] == 100 for arm in recovered["arms"].values())
        assert len((tmp_path / "runs.jsonl").read_text().splitlines()) == 6
    asyncio.run(check())


def test_invalid_gold_is_rejected_before_provider_call(tmp_path):
    class Fake:
        name, model, interval = "mock", "unused", 0
        async def generate(self, *args):
            raise AssertionError("Oracle audit must precede inference")
    cases = generate_cases()[:1]
    cases[0]["expected"]["arguments"]["travellers"] = -1
    with pytest.raises(ValueError, match="oracle"):
        asyncio.run(run(cases, Fake(), tmp_path))
