"""Suite runner: provider × case → assertion results."""

from __future__ import annotations

import itertools
from concurrent.futures import ThreadPoolExecutor
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


def expand_cases(cases: list[CaseSpec]) -> list[CaseSpec]:
    """Expand `matrix:` axes into concrete cases (cartesian product)."""
    expanded: list[CaseSpec] = []
    for case in cases:
        if not case.matrix:
            expanded.append(case)
            continue
        keys = list(case.matrix)
        for combo in itertools.product(*case.matrix.values()):
            label = ",".join(str(v) for v in combo)
            expanded.append(
                case.model_copy(
                    update={
                        "name": f"{case.name}[{label}]",
                        "vars": case.vars | dict(zip(keys, combo, strict=True)),
                        "matrix": {},
                    }
                )
            )
    return expanded


def run_suite(suite: SuiteSpec, max_workers: int = 1) -> SuiteResult:
    ctx = build_context(suite)
    cases = expand_cases(suite.cases)
    jobs = [(p, c) for p in suite.providers for c in cases]
    result = SuiteResult(suite.name)
    if max_workers <= 1:
        result.results = [run_case(p, c, ctx) for p, c in jobs]
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            result.results = list(pool.map(lambda job: run_case(*job, ctx), jobs))
    return result
