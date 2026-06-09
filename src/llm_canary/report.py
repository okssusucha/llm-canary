"""Reporters: console, JUnit XML, Markdown summary."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from llm_canary.baseline import Drift
from llm_canary.runner import SuiteResult
from llm_canary.trace import Violation

PASS = "PASS"
FAIL = "FAIL"


def console_report(result: SuiteResult, verbose: bool = False) -> str:
    lines = [f"suite: {result.suite}"]
    for r in result.results:
        mark = PASS if r.passed else FAIL
        lines.append(f"  [{mark}] {r.key}")
        if r.error:
            lines.append(f"         provider error: {r.error}")
        for a in r.assertions:
            if not a.passed:
                lines.append(f"         {a.type}: {a.message}")
            elif verbose:
                lines.append(f"         {a.type}: ok")
        if verbose and r.completion is not None:
            lines.append(
                f"         cost=${r.completion.cost_usd:.6f} "
                f"latency={r.completion.latency_ms:.0f}ms "
                f"tokens={r.completion.input_tokens}+{r.completion.output_tokens}"
            )
    ok, failed = result.counts
    lines.append(f"{ok} passed, {failed} failed")
    return "\n".join(lines)


def junit_report(result: SuiteResult, path: str | Path) -> None:
    ok, failed = result.counts
    suite_el = ET.Element(
        "testsuite",
        name=result.suite,
        tests=str(len(result.results)),
        failures=str(failed),
    )
    for r in result.results:
        case_el = ET.SubElement(suite_el, "testcase", classname=r.provider, name=r.case)
        if not r.passed:
            messages = [r.error] if r.error else []
            messages += [f"{a.type}: {a.message}" for a in r.assertions if not a.passed]
            failure = ET.SubElement(case_el, "failure", message="; ".join(messages))
            failure.text = "\n".join(messages)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(suite_el).write(path, encoding="unicode", xml_declaration=True)


def markdown_report(result: SuiteResult) -> str:
    ok, failed = result.counts
    status = "✅ all green" if failed == 0 else f"❌ {failed} failing"
    lines = [
        f"## llm-canary: `{result.suite}` — {status}",
        "",
        "| case | provider | result | detail |",
        "|---|---|---|---|",
    ]
    for r in result.results:
        if r.error:
            detail = r.error
        else:
            detail = "; ".join(f"{a.type}: {a.message}" for a in r.assertions if not a.passed)
        mark = "✅" if r.passed else "❌"
        lines.append(f"| {r.case} | {r.provider} | {mark} | {detail} |")
    lines.append("")
    lines.append(f"**{ok} passed, {failed} failed**")
    return "\n".join(lines)


def drift_report(drifts: list[Drift]) -> str:
    if not drifts:
        return "no drift: all cases within thresholds"
    lines = [f"{len(drifts)} drift(s) detected:"]
    lines += [f"  [{d.kind}] {d.key}: {d.message}" for d in drifts]
    return "\n".join(lines)


def violations_report(violations: list[Violation]) -> str:
    if not violations:
        return "trace OK: no policy violations"
    lines = [f"{len(violations)} violation(s):"]
    lines += [f"  [{v.rule}] {v.message}" for v in violations]
    return "\n".join(lines)
