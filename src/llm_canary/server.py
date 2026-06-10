"""Self-hosted llm-canary server.

Run with `llm-canary serve`. Everything stays inside your infrastructure:
suites, outputs, traces, and baselines are stored in a local SQLite file —
nothing is sent anywhere except the model providers you explicitly configure.

API:
    GET  /healthz
    POST /api/runs                      run a suite (JSON body = suite spec)
    GET  /api/runs                      run history
    GET  /api/runs/{id}                 full detail of one run
    POST /api/traces/check              check trace steps against a policy
    PUT  /api/baselines/{name}          run a suite and store it as baseline
    POST /api/baselines/{name}/check    rerun and report drift vs baseline
    GET  /                              minimal HTML dashboard
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from llm_canary import __version__
from llm_canary.baseline import baseline_data, check_drift
from llm_canary.config import SuiteSpec, TracePolicy
from llm_canary.report import result_dict
from llm_canary.runner import build_context, run_suite
from llm_canary.storage import Store
from llm_canary.trace import check_trace

DASHBOARD = """<!doctype html>
<html><head><meta charset="utf-8"><title>llm-canary</title>
<style>
body {{ font-family: ui-monospace, monospace; margin: 2rem; background: #0d1117; color: #e6edf3; }}
h1 {{ font-size: 1.2rem; }} a {{ color: #58a6ff; text-decoration: none; }}
table {{ border-collapse: collapse; width: 100%; }}
td, th {{ padding: .4rem .8rem; border-bottom: 1px solid #21262d; text-align: left; }}
.pass {{ color: #3fb950; }} .fail {{ color: #f85149; }}
</style></head><body>
<h1>llm-canary <small>v{version}</small></h1>
<table>
<tr><th>#</th><th>when (UTC)</th><th>kind</th><th>name</th><th>result</th><th>summary</th></tr>
{rows}
</table>
</body></html>"""


class TraceCheckRequest(BaseModel):
    steps: list[dict[str, Any]]
    policy: dict[str, Any] = Field(default_factory=dict)


class BaselineCheckRequest(BaseModel):
    suite: dict[str, Any]
    similarity_threshold: float = 0.8
    cost_drift_ratio: float = 0.2


def create_app(db_path: str = ".canary/canary.db") -> FastAPI:
    store = Store(db_path)
    app = FastAPI(title="llm-canary", version=__version__)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.post("/api/runs")
    def create_run(suite_spec: dict[str, Any]) -> dict[str, Any]:
        suite = SuiteSpec.model_validate(suite_spec)
        payload = result_dict(run_suite(suite))
        summary = f"{payload['ok']} passed, {payload['failed']} failed"
        run_id = store.add_run("suite", suite.name, payload["passed"], summary, payload)
        return {"id": run_id} | payload

    @app.get("/api/runs")
    def list_runs(limit: int = 50) -> list[dict[str, Any]]:
        return store.list_runs(limit)

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: int) -> dict[str, Any]:
        run = store.get_run(run_id)
        if run is None:
            raise HTTPException(404, f"run {run_id} not found")
        return run

    @app.post("/api/traces/check")
    def trace_check(req: TraceCheckRequest) -> dict[str, Any]:
        policy = TracePolicy.model_validate(req.policy)
        violations = [
            {"rule": v.rule, "message": v.message} for v in check_trace(req.steps, policy)
        ]
        payload = {"violations": violations, "steps": len(req.steps)}
        summary = f"{len(violations)} violation(s)" if violations else "no violations"
        run_id = store.add_run("trace", "trace", not violations, summary, payload)
        return {"id": run_id, "passed": not violations} | payload

    @app.put("/api/baselines/{name}")
    def record_baseline(name: str, suite_spec: dict[str, Any]) -> dict[str, Any]:
        suite = SuiteSpec.model_validate(suite_spec)
        data = baseline_data(run_suite(suite))
        store.set_baseline(name, data)
        return {"name": name, "cases": len(data["cases"])}

    @app.post("/api/baselines/{name}/check")
    def baseline_check(name: str, req: BaselineCheckRequest) -> dict[str, Any]:
        baseline = store.get_baseline(name)
        if baseline is None:
            raise HTTPException(404, f"baseline {name!r} not found — PUT it first")
        suite = SuiteSpec.model_validate(req.suite)
        drifts = check_drift(
            run_suite(suite),
            baseline,
            build_context(suite),
            similarity_threshold=req.similarity_threshold,
            cost_drift_ratio=req.cost_drift_ratio,
        )
        payload = {
            "drifts": [{"key": d.key, "kind": d.kind, "message": d.message} for d in drifts]
        }
        summary = f"{len(drifts)} drift(s)" if drifts else "no drift"
        run_id = store.add_run(f"baseline:{name}", suite.name, not drifts, summary, payload)
        return {"id": run_id, "passed": not drifts} | payload

    @app.get("/", response_class=HTMLResponse)
    def dashboard() -> str:
        rows = []
        for run in store.list_runs(100):
            cls, label = ("pass", "PASS") if run["passed"] else ("fail", "FAIL")
            rows.append(
                f"<tr><td><a href='/api/runs/{run['id']}'>{run['id']}</a></td>"
                f"<td>{run['created_at']}</td><td>{run['kind']}</td><td>{run['name']}</td>"
                f"<td class='{cls}'>{label}</td><td>{run['summary']}</td></tr>"
            )
        return DASHBOARD.format(version=__version__, rows="\n".join(rows))

    return app
