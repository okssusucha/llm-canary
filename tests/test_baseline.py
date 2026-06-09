from llm_canary.baseline import check_drift, load_baseline, save_baseline
from llm_canary.config import CaseSpec, ProviderSpec, SuiteSpec
from llm_canary.runner import run_suite
from llm_canary.runner_context import RunContext


def fixture_suite(reply: str) -> SuiteSpec:
    return SuiteSpec(
        name="b",
        providers=[ProviderSpec(name="fixture", options={"default": reply})],
        cases=[CaseSpec(name="c1", prompt="anything")],
    )


def test_record_then_check_no_drift(tmp_path):
    path = tmp_path / "baseline.json"
    save_baseline(run_suite(fixture_suite("stable answer")), path)
    drifts = check_drift(
        run_suite(fixture_suite("stable answer")), load_baseline(path), RunContext()
    )
    assert drifts == []


def test_output_drift_detected(tmp_path):
    path = tmp_path / "baseline.json"
    save_baseline(run_suite(fixture_suite("refund within 30 days of purchase")), path)
    drifts = check_drift(
        run_suite(fixture_suite("completely unrelated banana smoothie recipe")),
        load_baseline(path),
        RunContext(),
    )
    assert [d.kind for d in drifts] == ["output"]


def test_missing_baseline_case_flagged(tmp_path):
    path = tmp_path / "baseline.json"
    save_baseline(run_suite(fixture_suite("x")), path)
    suite = fixture_suite("x")
    suite.cases.append(CaseSpec(name="new-case", prompt="anything"))
    drifts = check_drift(run_suite(suite), load_baseline(path), RunContext())
    assert [d.kind for d in drifts] == ["missing"]


def test_cost_drift_detected(tmp_path):
    baseline = {"suite": "b", "cases": {"fixture/c1": {"text": "x", "cost_usd": 0.001}}}
    result = run_suite(fixture_suite("x"))
    result.results[0].completion.cost_usd = 0.01
    drifts = check_drift(result, baseline, RunContext())
    assert [d.kind for d in drifts] == ["cost"]
