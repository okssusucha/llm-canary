"""Assertion registry and runner."""

from __future__ import annotations

from dataclasses import dataclass

from llm_canary.assertions import basic, quality
from llm_canary.config import AssertionSpec
from llm_canary.providers.base import Completion
from llm_canary.runner_context import RunContext


@dataclass
class AssertionResult:
    type: str
    passed: bool
    message: str = ""


REGISTRY = {
    "contains": basic.check_contains,
    "not_contains": basic.check_not_contains,
    "regex": basic.check_regex,
    "equals": basic.check_equals,
    "json_valid": basic.check_json_valid,
    "json_schema": basic.check_json_schema,
    "max_latency_ms": basic.check_max_latency,
    "max_cost_usd": basic.check_max_cost,
    "max_output_tokens": basic.check_max_output_tokens,
    "similarity": quality.check_similarity,
    "judge": quality.check_judge,
}


def run_assertion(
    spec: AssertionSpec, completion: Completion, ctx: RunContext
) -> AssertionResult:
    try:
        fn = REGISTRY[spec.type]
    except KeyError:
        known = ", ".join(sorted(REGISTRY))
        return AssertionResult(spec.type, False, f"unknown assertion type (known: {known})")
    try:
        passed, message = fn(spec, completion, ctx)
    except Exception as exc:  # noqa: BLE001 - a broken assertion must fail the case, not the run
        return AssertionResult(spec.type, False, f"assertion error: {exc}")
    return AssertionResult(spec.type, passed, message)
