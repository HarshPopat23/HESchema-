import copy

import pytest

from heschema.dataset import generate_cases, values
from heschema.domains import DOMAINS, reference_schema
from heschema.jsonio import loads
from heschema.schema import SchemaEngine, check_schema, child_environment, typed_minimal
from heschema.validation import CompiledState, envelope, evaluate, policy_errors


@pytest.fixture
def engine():
    obj = SchemaEngine()
    yield obj
    obj.close()


@pytest.mark.parametrize("case", generate_cases(), ids=lambda c: c["id"])
def test_every_benchmark_oracle(case, engine):
    ref = reference_schema(case["domain"])
    result = evaluate(case["expected"], engine, ref, ref, case["expected"],
                      policy=DOMAINS[case["domain"]]["policy"])
    assert result["success"]
    assert result["executionAuthorized"] is False


@pytest.mark.parametrize("raw", ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":1e9999}', '{"x":', '```json\n{}\n```'])
def test_strict_json_rejects(raw):
    with pytest.raises(ValueError):
        loads(raw)


def test_wrong_destination_is_structurally_valid_but_semantically_wrong(engine):
    args = values("flights", 0)
    gold = envelope("call_tool", "search_flights", args)
    wrong = copy.deepcopy(gold)
    wrong["arguments"]["destination"] = "Pune"
    result = evaluate(wrong, engine, reference_schema("flights"), reference_schema("flights"), gold, args)
    assert result["referenceSchemaValid"]
    assert not result["semanticValid"]
    assert result["result"] == "FAIL"
    assert "STATE_MISMATCH" in {e["code"] for e in result["errors"]}


def test_permissive_candidate_cannot_make_wrong_answer_pass(engine):
    gold = envelope("call_tool", "search_flights", values("flights", 0))
    wrong = copy.deepcopy(gold)
    wrong["arguments"]["travellers"] = -1
    result = evaluate(wrong, engine, reference_schema("flights"), {}, gold)
    assert result["candidateSchemaValid"]
    assert not result["referenceSchemaValid"]
    assert not result["success"]


def test_contradictory_candidate_does_not_change_common_benchmark_judge(engine):
    gold = envelope("call_tool", "search_flights", values("flights", 0))
    result = evaluate(gold, engine, reference_schema("flights"), False, gold)
    assert not result["candidateSchemaValid"]
    assert result["success"]  # Runtime adds a separate candidate gate.


@pytest.mark.parametrize("field,value", [("departureDate", "2027-02-30"), ("travellers", True), ("travellers", 10)])
def test_formats_types_bounds(engine, field, value):
    args = values("flights", 0)
    args[field] = value
    assert engine.errors(reference_schema("flights"), args)


def test_missing_and_extra_envelope_properties(engine):
    gold = envelope("refuse")
    assert not evaluate({"action": "refuse"}, engine, {}, {}, gold)["success"]
    assert not evaluate({**gold, "unexpected": 1}, engine, {}, {}, gold)["success"]


def test_compiled_state_is_immutable_and_bool_is_not_one():
    state = {"count": 1, "nested": {"city": "Goa"}}
    compiled = CompiledState.compile(state)
    state["nested"]["city"] = "Pune"
    assert not compiled.errors({"count": 1, "nested": {"city": "Goa"}})
    assert compiled.errors({"count": True, "nested": {"city": "Goa"}})


def test_policies():
    assert policy_errors({"amountMinor": 100001}, {"max": {"amountMinor": 100000}})
    assert policy_errors({"a": "2027-01-02", "b": "2027-01-01"}, {"ordered": [["a", "b"]]})
    assert not policy_errors({"a": "2027-01-01", "b": "2027-01-02"}, {"ordered": [["a", "b"]]})


@pytest.mark.parametrize("schema", [{"type": "not-a-type"}, {"$ref": "https://example.org/schema"}, {"$schema": "http://json-schema.org/draft-07/schema#"}])
def test_schema_registration_rejects_invalid_or_network_refs(schema):
    with pytest.raises(ValueError):
        check_schema(schema)


def test_minimal_keeps_meanings_and_required_but_removes_constraints():
    schema = typed_minimal(reference_schema("flights"))
    assert "required" in schema
    assert schema["properties"]["travellers"]["type"] == "integer"
    assert "minimum" not in schema["properties"]["travellers"]


def test_cache_is_bounded():
    engine = SchemaEngine(capacity=2)
    for schema in ({"type": "integer"}, {"type": "string"}, {"type": "array"}):
        engine.register(schema)
    assert len(engine.cache) == 2


def test_native_child_does_not_inherit_keys(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-only-secret")
    monkeypatch.setenv("HESCHEMA_API_TOKEN", "test-only-secret")
    assert "GROQ_API_KEY" not in child_environment()
    assert "HESCHEMA_API_TOKEN" not in child_environment()
