import asyncio

import pytest

from heschema.benchmark import messages_for, mutation_probes, run
from heschema.dataset import audit, generate_cases, load_cases
from heschema.domains import reference_schema
from heschema.jsonio import canonical, loads
from heschema.providers import Generation, Provider
from heschema.schema import SchemaEngine


def test_dataset_count_provenance_and_reproducibility():
    cases = generate_cases()
    assert len(cases) == 480 and cases == generate_cases()
    assert audit(cases)["uniquePrompts"] == 480
    assert all(not c["humanReviewed"] for c in cases)


def test_hidden_expected_never_in_prompt():
    case = generate_cases()[0]
    case["expected"]["reason"] = "SECRET_ORACLE_SENTINEL"
    assert "SECRET_ORACLE_SENTINEL" not in canonical(messages_for(case, reference_schema("flights")))
    assert "Argument JSON Schema" not in canonical(messages_for(case, None))


def test_probes_expose_weak_and_contradictory_schemas():
    cases = generate_cases()[:5]
    engine = SchemaEngine()
    weak = mutation_probes(cases, {"flights": {}}, engine)
    assert weak["invalidRejectionPercent"] == 0
    bad = mutation_probes(cases, {"flights": False}, engine)
    assert bad["falseRejectionPercent"] == 100
    good = mutation_probes(cases, {"flights": reference_schema("flights")}, engine)
    assert good["invalidRejectionPercent"] == 100 and good["falseRejectionPercent"] == 0


def test_mock_smoke_resume_budget_and_no_empirical_claim(tmp_path):
    async def experiment():
        provider = Provider("mock", interval=0)
        try:
            cases = generate_cases()[:4]
            partial = await run(cases, provider, tmp_path, repeats=1, repairs=0, max_requests=5)
            assert not partial["complete"] and partial["completedRuns"] == 5
            result = await run(cases, provider, tmp_path, repeats=1, repairs=0)
            assert result["complete"] and result["completedRuns"] == 12
            assert not result["empiricalLLMEvidence"] and not result["comparisonValid"]
            assert result["arms"]["input_schema"]["callSchemaValidityPercent"] == 0
            assert result["arms"]["input_schema"]["semanticPrecisionAmongValidCallsPercent"] is None
            again = await run(cases, provider, tmp_path, repeats=1, repairs=0)
            assert again["completedRuns"] == 12
            with pytest.raises(ValueError, match="Resume"):
                await run(cases, provider, tmp_path, repeats=2, repairs=0)
        finally:
            await provider.close()
    asyncio.run(experiment())


def test_repair_has_no_oracle_values_and_silent_intent_error_not_repaired(tmp_path):
    case = generate_cases()[0]

    class Fake:
        name, model, interval = "mock", "fake-for-unit-test", 0
        def __init__(self):
            self.calls = []
        async def generate(self, messages, *args):
            self.calls.append(messages.copy())
            wrong = loads(canonical(case["expected"]))
            wrong["arguments"]["destination"] = "Pune"
            return Generation(canonical(wrong), 10, 10, self.model)
    provider = Fake()
    result = asyncio.run(run([case], provider, tmp_path, repeats=1, repairs=2))
    assert len(provider.calls) == 3  # One per arm, no oracle-driven correction.
    assert result["arms"]["input_schema"]["firstPassSuccessPercent"] == 0


def test_duplicate_dataset_ids_rejected(tmp_path):
    path = tmp_path / "cases.jsonl"
    path.write_text('{"id":"x"}\n{"id":"x"}\n')
    with pytest.raises(ValueError):
        load_cases(path)
