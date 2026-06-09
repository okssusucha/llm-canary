from llm_canary.config import AssertionSpec, CaseSpec, ProviderSpec, SuiteSpec
from llm_canary.runner import run_suite


def make_suite(**overrides) -> SuiteSpec:
    base = dict(
        name="t",
        providers=[ProviderSpec(name="echo")],
        cases=[
            CaseSpec(
                name="greet",
                prompt="say hello to {who}",
                vars={"who": "yui"},
                assertions=[AssertionSpec(type="contains", value="yui")],
            )
        ],
    )
    base.update(overrides)
    return SuiteSpec(**base)


def test_run_suite_passes():
    result = run_suite(make_suite())
    assert result.passed
    assert result.counts == (1, 0)
    assert result.results[0].key == "echo/greet"


def test_vars_are_rendered_into_prompt():
    result = run_suite(make_suite())
    assert "yui" in result.results[0].completion.text


def test_failing_assertion_fails_suite():
    suite = make_suite(
        cases=[
            CaseSpec(
                name="bad",
                prompt="hello",
                assertions=[AssertionSpec(type="contains", value="absent-text")],
            )
        ]
    )
    result = run_suite(suite)
    assert not result.passed
    assert result.counts == (0, 1)


def test_provider_error_becomes_case_failure():
    suite = make_suite(
        providers=[ProviderSpec(name="fixture", options={"responses": []})],
    )
    result = run_suite(suite)
    assert not result.passed
    assert "no rule" in result.results[0].error


def test_multiple_providers_fan_out():
    suite = make_suite(
        providers=[
            ProviderSpec(name="echo"),
            ProviderSpec(name="fixture", options={"default": "hello yui"}),
        ]
    )
    result = run_suite(suite)
    assert len(result.results) == 2
    assert result.passed


def test_unknown_provider_is_case_error():
    suite = make_suite(providers=[ProviderSpec(name="nope")])
    result = run_suite(suite)
    assert not result.passed
    assert "unknown provider" in result.results[0].error
