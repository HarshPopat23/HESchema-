import pytest

from heschema.schema import check_schema
from heschema.security import check_regex_safety, check_schema_complexity
from heschema.state import StateStore


def test_schema_depth_limit():
    # Build deep schema beyond max_depth=15
    deep = {"type": "string"}
    for _ in range(18):
        deep = {"type": "object", "properties": {"nested": deep}}

    with pytest.raises(ValueError, match="exceeds complexity budget limit"):
        check_schema_complexity(deep, max_depth=15)

    # Moderate depth should pass
    normal = {"type": "object", "properties": {"a": {"type": "object", "properties": {"b": {"type": "string"}}}}}
    check_schema_complexity(normal, max_depth=15)


def test_schema_property_count_limit():
    # 260 properties
    props = {f"prop_{i}": {"type": "string"} for i in range(260)}
    schema = {"type": "object", "properties": props}

    with pytest.raises(ValueError, match="Total schema property count"):
        check_schema_complexity(schema, max_properties=250)


def test_schema_regex_redos_detection():
    # Catastrophic backtracking patterns
    dangerous = ["(a+)+$", "((a|aa)+)+", "(.*)+tail"]
    for pat in dangerous:
        with pytest.raises(ValueError, match="catastrophic backtracking"):
            check_regex_safety(pat)

    # Safe regexes
    safe = [r"^[a-zA-Z0-9_-]+$", r"^\d{4}-\d{2}-\d{2}$", r"^[a-z]+@[a-z]+\.[a-z]+$"]
    for pat in safe:
        check_regex_safety(pat)


def test_check_schema_rejects_redos_in_pattern():
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "vulnerable": {
                "type": "string",
                "pattern": "(a+)+$",
            }
        },
    }
    with pytest.raises(ValueError, match="catastrophic backtracking"):
        check_schema(schema)


def test_atomic_state_transitions(tmp_path):
    store = StateStore(tmp_path / "test_state.sqlite")
    created = store.create("user1", "task-prompt", {"count": 10})
    state_id = created["id"]
    version = created["version"]

    assert created["confirmed"] is False

    # Confirm once
    confirmed = store.confirm(state_id, "user1", version)
    assert confirmed["confirmed"] is True

    # Confirming again with same stale version should fail
    # (replace creates version 2, then confirm updates)
    replaced = store.replace(state_id, "user1", version, {"count": 20})
    assert replaced["version"] == 2
    assert replaced["confirmed"] is False

    # Stale version 1 fails
    with pytest.raises(ValueError, match="Stale state or unknown owner"):
        store.replace(state_id, "user1", 1, {"count": 30})

    # Valid version 2 confirms atomically
    final_confirmed = store.confirm(state_id, "user1", 2)
    assert final_confirmed["confirmed"] is True
    assert final_confirmed["state"] == {"count": 20}
