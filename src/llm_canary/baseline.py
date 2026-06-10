"""Baseline recording and drift checking.

``record`` snapshots each case's output and cost; ``check`` reruns the suite
and flags cases whose output drifted below a similarity threshold or whose
cost grew beyond an allowed ratio. This is the regression-canary core: you
don't need golden answers, just "it changed more than I allowed".
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from llm_canary.runner import SuiteResult
from llm_canary.runner_context import RunContext
from llm_canary.semantic import similarity

DEFAULT_BASELINE = Path(".canary/baseline.json")


@dataclass
class Drift:
    key: str
    kind: str  # "output" | "cost" | "missing"
    message: str


def baseline_data(result: SuiteResult) -> dict:
    cases = {
        r.key: {
            "text": r.completion.text if r.completion else "",
            "cost_usd": r.completion.cost_usd if r.completion else 0.0,
        }
        for r in result.results
    }
    return {"suite": result.suite, "cases": cases}


def save_baseline(result: SuiteResult, path: str | Path = DEFAULT_BASELINE) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(baseline_data(result), indent=2))


def load_baseline(path: str | Path = DEFAULT_BASELINE) -> dict:
    return json.loads(Path(path).read_text())


def check_drift(
    result: SuiteResult,
    baseline: dict,
    ctx: RunContext,
    similarity_threshold: float = 0.8,
    cost_drift_ratio: float = 0.2,
) -> list[Drift]:
    drifts: list[Drift] = []
    cases = baseline.get("cases", {})
    for r in result.results:
        base = cases.get(r.key)
        if base is None:
            drifts.append(Drift(r.key, "missing", "no baseline recorded (run `record` first)"))
            continue
        if r.completion is None:
            drifts.append(Drift(r.key, "output", f"case errored: {r.error}"))
            continue
        score = similarity(ctx.embedder, r.completion.text, base["text"])
        if score < similarity_threshold:
            drifts.append(
                Drift(
                    r.key,
                    "output",
                    f"output drifted: similarity {score:.3f} < {similarity_threshold:.3f}",
                )
            )
        base_cost = float(base.get("cost_usd", 0.0))
        if base_cost > 0 and r.completion.cost_usd > base_cost * (1 + cost_drift_ratio):
            drifts.append(
                Drift(
                    r.key,
                    "cost",
                    f"cost ${r.completion.cost_usd:.6f} > baseline ${base_cost:.6f} "
                    f"+{cost_drift_ratio:.0%}",
                )
            )
    return drifts
