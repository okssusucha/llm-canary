from llm_canary.assertions import run_assertion
from llm_canary.config import AssertionSpec
from llm_canary.providers.base import Completion
from llm_canary.runner_context import RunContext


def make(text="hello world", **kw):
    return Completion(text=text, **kw)


CTX = RunContext()


def run(completion, **spec):
    return run_assertion(AssertionSpec(**spec), completion, CTX)


def test_contains_pass_and_fail():
    assert run(make(), type="contains", value="hello").passed
    result = run(make(), type="contains", value="goodbye")
    assert not result.passed
    assert "goodbye" in result.message


def test_contains_case_insensitive():
    assert run(make("HELLO"), type="contains", value="hello", case_insensitive=True).passed


def test_not_contains():
    assert run(make(), type="not_contains", value="password").passed
    assert not run(make("the password is 123"), type="not_contains", value="password").passed


def test_regex():
    assert run(make("order #4521 shipped"), type="regex", value=r"#\d+").passed
    assert not run(make("no order id"), type="regex", value=r"#\d+").passed


def test_equals_strips_whitespace():
    assert run(make("  yes\n"), type="equals", value="yes").passed
    assert not run(make("no"), type="equals", value="yes").passed


def test_json_valid_handles_fences_and_prose():
    assert run(make('{"a": 1}'), type="json_valid").passed
    assert run(make('Sure! ```json\n{"a": 1}\n```'), type="json_valid").passed
    assert run(make('Here you go: {"a": 1}'), type="json_valid").passed
    assert not run(make("not json at all"), type="json_valid").passed


def test_json_schema():
    schema = {"type": "object", "required": ["eligible"]}
    assert run(make('{"eligible": true}'), type="json_schema", value=schema).passed
    result = run(make('{"other": 1}'), type="json_schema", value=schema)
    assert not result.passed
    assert "eligible" in result.message


def test_budget_assertions():
    c = make(latency_ms=120.0, cost_usd=0.002, output_tokens=50)
    assert run(c, type="max_latency_ms", value=500).passed
    assert not run(c, type="max_latency_ms", value=100).passed
    assert run(c, type="max_cost_usd", value=0.01).passed
    assert not run(c, type="max_cost_usd", value=0.001).passed
    assert run(c, type="max_output_tokens", value=100).passed
    assert not run(c, type="max_output_tokens", value=10).passed


def test_unknown_assertion_fails_gracefully():
    result = run(make(), type="nope")
    assert not result.passed
    assert "unknown assertion" in result.message
