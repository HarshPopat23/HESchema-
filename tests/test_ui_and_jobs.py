from fastapi.testclient import TestClient

from heschema.api import create_app
from heschema.dataset import values
from heschema.metrics import paired_effect


def test_ui_assets_served_without_breaking_docs(tmp_path, monkeypatch):
    monkeypatch.delenv("HESCHEMA_API_TOKEN", raising=False)
    with TestClient(create_app(tmp_path / "state.sqlite")) as client:
        # 1. UI Root
        res_index = client.get("/")
        assert res_index.status_code == 200
        assert "HESchema" in res_index.text
        assert "tab-btn-prompt" in res_index.text

        # 2. Static CSS and JS
        res_css = client.get("/static/styles.css")
        assert res_css.status_code == 200
        assert "--accent-color" in res_css.text

        res_js = client.get("/static/app.js")
        assert res_js.status_code == 200
        assert "runSinglePrompt" in res_js.text

        # 3. Docs and OpenAPI routes preserved
        assert client.get("/docs").status_code == 200
        openapi = client.get("/openapi.json").json()
        assert openapi["info"]["title"] == "HESchema"


def test_schema_validation_endpoint(tmp_path, monkeypatch):
    monkeypatch.delenv("HESCHEMA_API_TOKEN", raising=False)
    with TestClient(create_app(tmp_path / "state.sqlite")) as client:
        # Valid draft 2020-12
        valid = {"type": "object", "properties": {"name": {"type": "string"}}}
        res = client.post("/ui/validate-schema", json={"schema": valid})
        assert res.status_code == 200
        assert res.json()["valid"] is True

        # Invalid JSON schema
        invalid = {"type": "unsupported_type_xyz"}
        res = client.post("/ui/validate-schema", json={"schema": invalid})
        assert res.status_code == 200
        assert res.json()["valid"] is False
        assert "Invalid JSON Schema" in res.json()["error"]


def test_prompt_test_invalid_schema_rejected_before_inference(tmp_path, monkeypatch):
    monkeypatch.delenv("HESCHEMA_API_TOKEN", raising=False)
    with TestClient(create_app(tmp_path / "state.sqlite")) as client:
        res = client.post(
            "/ui/prompt-test",
            json={
                "prompt": "Find flights from Delhi to Mumbai",
                "domain": "flights",
                "provider": "mock",
                "schemaMode": "supplied_schema",
                "schema": {"type": "broken_primitive"},
            },
        )
        assert res.status_code == 422
        assert "Invalid schema" in res.text


def test_prompt_test_missing_provider_fails_safely(tmp_path, monkeypatch):
    monkeypatch.delenv("HESCHEMA_API_TOKEN", raising=False)
    with TestClient(create_app(tmp_path / "state.sqlite")) as client:
        res = client.post(
            "/ui/prompt-test",
            json={
                "prompt": "Find flights",
                "domain": "flights",
                "provider": "non_existent_provider_123",
            },
        )
        assert res.status_code == 422


def test_true_no_schema_generation_and_unconfirmed_state(tmp_path, monkeypatch):
    monkeypatch.delenv("HESCHEMA_API_TOKEN", raising=False)
    with TestClient(create_app(tmp_path / "state.sqlite")) as client:
        # Generation without state: semanticValid must be None, result cannot be PASS
        res = client.post(
            "/ui/prompt-test",
            json={
                "prompt": "Find flights from Jaipur to Goa on 2027-01-01 for 1 traveller",
                "domain": "flights",
                "provider": "mock",
                "schemaMode": "no_schema",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["model"] == "offline-stub"
        val = data["validation"]
        assert val["semanticChecked"] is False
        assert val["semanticValid"] is None
        # Mock stub returns refuse, which doesn't match complete search, so result is not PASS
        assert val["result"] != "PASS"


def test_confirmed_state_agreement_and_destination_mismatch(tmp_path, monkeypatch):
    monkeypatch.delenv("HESCHEMA_API_TOKEN", raising=False)
    with TestClient(create_app(tmp_path / "state.sqlite")) as client:
        args = values("flights", 0)  # origin: Jaipur, destination: Goa
        snap = client.post("/states", json={"prompt": "Jaipur to Goa", "state": args}).json()
        client.post(f"/states/{snap['id']}/confirm", json={"version": 1})

        # Validate with wrong destination
        wrong_args = {**args, "destination": "Pune"}
        from heschema.validation import envelope

        val_res = client.post(
            "/validate",
            json={
                "stateId": snap["id"],
                "stateVersion": 1,
                "domain": "flights",
                "output": envelope("call_tool", "search_flights", wrong_args),
            },
        ).json()
        assert val_res["result"] == "FAIL"
        assert val_res["semanticValid"] is False
        assert any(e.get("code") == "STATE_MISMATCH" for e in val_res["errors"])


def test_single_prompt_compare_requires_confirmed_state(tmp_path, monkeypatch):
    monkeypatch.delenv("HESCHEMA_API_TOKEN", raising=False)
    with TestClient(create_app(tmp_path / "state.sqlite")) as client:
        args = values("flights", 0)
        snap = client.post("/states", json={"prompt": "Jaipur to Goa", "state": args}).json()
        # Unconfirmed -> 409
        res_unconf = client.post(
            "/ui/prompt-compare",
            json={
                "prompt": "Find flights",
                "domain": "flights",
                "provider": "mock",
                "stateId": snap["id"],
                "stateVersion": 1,
                "repeats": 1,
            },
        )
        assert res_unconf.status_code == 409

        # Confirm state
        client.post(f"/states/{snap['id']}/confirm", json={"version": 1})
        res_conf = client.post(
            "/ui/prompt-compare",
            json={
                "prompt": "Find flights",
                "domain": "flights",
                "provider": "mock",
                "stateId": snap["id"],
                "stateVersion": 1,
                "repeats": 1,
            },
        )
        assert res_conf.status_code == 200
        data = res_conf.json()
        assert data["trialType"] == "Single-prompt trial"
        assert "no_schema" in data["arms"]
        assert "minimal_schema" in data["arms"]
        assert "input_schema" in data["arms"]


def test_jobs_api_concurrency_and_cancellation(tmp_path, monkeypatch):
    monkeypatch.delenv("HESCHEMA_API_TOKEN", raising=False)
    with TestClient(create_app(tmp_path / "state.sqlite")) as client:
        # Start a quick mock job
        job_res = client.post(
            "/ui/jobs",
            json={
                "domain": "flights",
                "provider": "mock",
                "preset": "quick",
                "repeats": 1,
                "repairs": 0,
            },
        )
        assert job_res.status_code == 200
        job_id = job_res.json()["id"]

        # Check job status
        status_res = client.get(f"/ui/jobs/{job_id}")
        assert status_res.status_code == 200
        assert status_res.json()["id"] == job_id

        # Cancel job
        cancel_res = client.post(f"/ui/jobs/{job_id}/cancel")
        assert cancel_res.status_code == 200
        assert cancel_res.json()["status"] in {"cancelled", "completed"}


def test_canonical_examples(tmp_path, monkeypatch):
    monkeypatch.delenv("HESCHEMA_API_TOKEN", raising=False)
    with TestClient(create_app(tmp_path / "state.sqlite")) as client:
        # Flights
        ex_f = client.get("/ui/examples/flights").json()
        assert "origin" in ex_f["state"]
        assert "destination" in ex_f["state"]

        # Payments - integer minor units
        ex_p = client.get("/ui/examples/payments").json()
        assert isinstance(ex_p["state"]["amountMinor"], int)
        assert ex_p["state"]["amountMinor"] == 75050
        assert ex_p["state"]["currency"] == "INR"


def test_metrics_zero_uplift_interval_crossing_zero():
    # If both baseline and treatment have equal success, uplift is 0 and interval crosses 0
    rows = [
        {"caseId": "c1", "cluster": "cl1", "repeat": 0, "arm": "no_schema", "firstPassSuccess": True},
        {"caseId": "c1", "cluster": "cl1", "repeat": 0, "arm": "input_schema", "firstPassSuccess": True},
        {"caseId": "c2", "cluster": "cl2", "repeat": 0, "arm": "no_schema", "firstPassSuccess": False},
        {"caseId": "c2", "cluster": "cl2", "repeat": 0, "arm": "input_schema", "firstPassSuccess": False},
    ]
    eff = paired_effect(rows, "no_schema", "input_schema")
    assert eff["absoluteUpliftPoints"] == 0.0
    assert eff["effect"] == "inconclusive"
    assert eff["confidenceInterval95"][0] <= 0
    assert eff["confidenceInterval95"][1] >= 0
