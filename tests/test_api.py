from fastapi.testclient import TestClient

from heschema.api import create_app
from heschema.dataset import values
from heschema.state import StateStore
from heschema.validation import envelope


def test_store_ownership_version_and_confirmation(tmp_path):
    store = StateStore(tmp_path / "state.sqlite")
    snap = store.create("alice", "Goa", {"destination": "Goa"})
    assert not snap["confirmed"]
    import pytest
    with pytest.raises(KeyError):
        store.get(snap["id"], "bob")
    assert store.confirm(snap["id"], "alice", 1)["confirmed"]
    changed = store.replace(snap["id"], "alice", 1, {"destination": "Pune"})
    assert changed["version"] == 2 and not changed["confirmed"]
    with pytest.raises(ValueError):
        store.confirm(snap["id"], "alice", 1)


def test_full_runtime_gate(tmp_path, monkeypatch):
    monkeypatch.delenv("HESCHEMA_API_TOKEN", raising=False)
    monkeypatch.setenv("HESCHEMA_ENGINE", "jsonschema")
    args = values("flights", 0)
    with TestClient(create_app(tmp_path / "state.sqlite")) as client:
        snap = client.post("/states", json={"prompt": "Jaipur to Goa", "state": args}).json()
        body = {"stateId": snap["id"], "stateVersion": 1, "domain": "flights", "output": envelope("call_tool", "search_flights", args)}
        assert client.post("/validate", json=body).status_code == 409
        assert client.post(f"/states/{snap['id']}/confirm", json={"version": 1}).status_code == 200
        result = client.post("/validate", json=body).json()
        assert result["result"] == "PASS" and not result["executionAuthorized"]
        candidate_fail = client.post("/validate", json={**body, "schema": False}).json()
        assert candidate_fail["result"] == "FAIL" and candidate_fail["benchmarkSuccess"]
        invalid = client.post("/validate", json={**body, "schema": {"type": "nonsense"}})
        assert invalid.status_code == 422
        wrong = {**args, "destination": "Pune"}
        assert client.post("/validate", json={**body, "output": envelope("call_tool", "search_flights", wrong)}).json()["result"] == "FAIL"
        change = client.put(f"/states/{snap['id']}", json={"version": 1, "state": wrong}).json()
        assert change["version"] == 2 and not change["confirmed"]
        assert client.post("/validate", json=body).status_code == 409
        assert client.get("/openapi.json").json()["openapi"].startswith("3.")


def test_api_token_required(tmp_path, monkeypatch):
    monkeypatch.setenv("HESCHEMA_API_TOKEN", "test-only-token")
    with TestClient(create_app(tmp_path / "state.sqlite")) as client:
        assert client.get("/providers").status_code == 401
        assert client.get("/providers", headers={"Authorization": "Bearer test-only-token"}).status_code == 200


def test_mock_generate_and_extract_do_not_authorize_or_confirm(tmp_path, monkeypatch):
    monkeypatch.delenv("HESCHEMA_API_TOKEN", raising=False)
    with TestClient(create_app(tmp_path / "state.sqlite")) as client:
        proposal = client.post("/extract", json={"prompt": "Jaipur to Goa", "domain": "flights", "provider": "mock"}).json()
        assert not proposal["confirmed"] and proposal["state"] is None
        snap = client.post("/states", json={"prompt": "Jaipur to Goa", "state": values("flights", 0)}).json()
        client.post(f"/states/{snap['id']}/confirm", json={"version": 1})
        result = client.post("/generate", json={"stateId": snap["id"], "stateVersion": 1, "domain": "flights", "provider": "mock"}).json()
        assert result["validation"]["result"] == "FAIL"
