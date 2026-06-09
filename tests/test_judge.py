from llm_canary.assertions import run_assertion
from llm_canary.config import AssertionSpec, ProviderSpec
from llm_canary.providers import build_provider
from llm_canary.providers.base import Completion
from llm_canary.runner_context import RunContext


def judge_ctx(verdict: str) -> RunContext:
    spec = ProviderSpec(name="fixture", options={"default": verdict})
    return RunContext(judge_provider=build_provider(spec))


def run_judge(ctx, threshold=None):
    spec = AssertionSpec(type="judge", value="is polite", threshold=threshold)
    return run_assertion(spec, Completion(text="thank you for asking!"), ctx)


def test_judge_passes_above_threshold():
    assert run_judge(judge_ctx('{"score": 0.9, "reason": "polite"}')).passed


def test_judge_fails_below_threshold():
    result = run_judge(judge_ctx('{"score": 0.2, "reason": "rude"}'))
    assert not result.passed
    assert "rude" in result.message


def test_judge_verdict_wrapped_in_prose():
    assert run_judge(judge_ctx('Verdict: {"score": 1.0, "reason": "ok"} done')).passed


def test_judge_unparseable_verdict_fails():
    assert not run_judge(judge_ctx("I think it is fine")).passed


def test_judge_without_provider_fails_with_hint():
    result = run_judge(RunContext())
    assert not result.passed
    assert "judge" in result.message


def test_custom_threshold():
    assert run_judge(judge_ctx('{"score": 0.5}'), threshold=0.4).passed
    assert not run_judge(judge_ctx('{"score": 0.5}'), threshold=0.6).passed
