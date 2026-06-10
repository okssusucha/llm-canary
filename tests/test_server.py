import pytest
from fastapi.testclient import TestClient

from llm_canary.server import create_app

SUITE = {
    "name": "api-suite",
    "providers": [{"name": "echo"}],
    "cases": [
        {
            "name": "greet",
            "prompt": "hello there",
            "assertions": [{"type": "contains", "value": "hello"}],
        }
    ],
}

FAILING_SUITE = {
    **SUITE,
    "cases": [
        {
            "name": "greet",
            "prompt": "hello there",
            "assertions": [{"type": "contains", "value": "absent-text"}],
        }
    ],
}


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(str(tmp_path / "canary.db")))


def test_healthz(client):
    body = client.get("/healthz").json()
    assert body["status"] == "ok"


def test_run_suite_and_history(client):
    body = client.post("/api/runs", json=SUITE).json()
    assert body["passed"] is True
    assert body["ok"] == 1
    runs = client.get("/api/runs").json()
    assert len(runs) == 1
    assert runs[0]["name"] == "api-suite"
    detail = client.get(f"/api/runs/{body['id']}").json()
    assert detail["payload"]["results"][0]["case"] == "greet"


def test_failing_suite_recorded_as_failed(client):
    body = client.post("/api/runs", json=FAILING_SUITE).json()
    assert body["passed"] is False
    assert client.get("/api/runs").json()[0]["passed"] is False


def test_get_unknown_run_is_404(client):
    assert client.get("/api/runs/999").status_code == 404


def test_trace_check(client):
    steps = [{"type": "tool_call", "tool": "search"}]
    ok = client.post("/api/traces/check", json={"steps": steps, "policy": {"max_steps": 5}})
    assert ok.json()["passed"] is True
    bad = client.post(
        "/api/traces/check",
        json={"steps": steps, "policy": {"forbidden_tools": ["search"]}},
    )
    assert bad.json()["passed"] is False
    assert bad.json()["violations"][0]["rule"] == "forbidden_tools"


def test_baseline_record_and_check(client):
    recorded = client.put("/api/baselines/main", json=SUITE).json()
    assert recorded["cases"] == 1
    checked = client.post("/api/baselines/main/check", json={"suite": SUITE}).json()
    assert checked["passed"] is True
    assert checked["drifts"] == []


def test_baseline_check_detects_drift(client):
    client.put("/api/baselines/main", json=SUITE)
    drifted = {
        **SUITE,
        "cases": [{"name": "greet", "prompt": "completely different banana topic"}],
    }
    body = client.post("/api/baselines/main/check", json={"suite": drifted}).json()
    assert body["passed"] is False
    assert body["drifts"][0]["kind"] == "output"


def test_baseline_check_missing_is_404(client):
    assert client.post("/api/baselines/nope/check", json={"suite": SUITE}).status_code == 404


def test_dashboard_lists_runs(client):
    client.post("/api/runs", json=SUITE)
    html = client.get("/").text
    assert "api-suite" in html
    assert "PASS" in html
