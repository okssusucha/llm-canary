"""Suite runner: provider × case → assertion results."""

from __future__ import annotations

from dataclasses import dataclass, field

from llm_canary.assertions import AssertionResult, run_assertion
from llm_canary.config import CaseSpec, ProviderSpec, SuiteSpec
from llm_canary.providers import build_provider
from llm_canary.providers.base import Completion
from llm_canary.runner_context import RunContext


@dataclass
class CaseResult:
    provider: str
    case: str
    completion: Completion | None
    assertions: list[AssertionResult] = field(default_factory=list)
    error: str = ""

    @property
    def passed(self) -> bool:
        return not self.error and all(a.passed for a in self.assertions)

    @property
    def key(self) -> str:
        return f"{self.provider}/{self.case}"


@dataclass
class SuiteResult:
    suite: str
    results: list[CaseResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def counts(self) -> tuple[int, int]:
        ok = sum(1 for r in self.results if r.passed)
        return ok, len(self.results) - ok


def build_context(suite: SuiteSpec) -> RunContext:
    ctx = RunContext()
    if suite.judge is not None:
        ctx.judge_provider = build_provider(suite.judge)
    return ctx


def run_case(provider_spec: ProviderSpec, case: CaseSpec, ctx: RunContext) -> CaseResult:
    try:
        provider = build_provider(provider_spec)
        completion = provider.complete(case.rendered_prompt())
    except Exception as exc:  # noqa: BLE001 - a provider failure fails the case, not the run
        return CaseResult(provider_spec.key, case.name, None, error=str(exc))
    assertions = [run_assertion(spec, completion, ctx) for spec in case.assertions]
    return CaseResult(provider_spec.key, case.name, completion, assertions)


def run_suite(suite: SuiteSpec) -> SuiteResult:
    ctx = build_context(suite)
    result = SuiteResult(suite.name)
    for provider_spec in suite.providers:
        for case in suite.cases:
            result.results.append(run_case(provider_spec, case, ctx))
    return result
