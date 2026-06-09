"""Agent-trace policy checks.

A trace is a JSONL file, one step per line, e.g.:

    {"type": "tool_call", "tool": "search_docs", "cost_usd": 0.001}
    {"type": "message", "role": "assistant", "cost_usd": 0.002}

The policy (see ``TracePolicy``) gates what an agent was allowed to do:
step budget, cost budget, forbidden/required tools, ordering, loop limits.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from llm_canary.config import TracePolicy


@dataclass
class Violation:
    rule: str
    message: str


def load_trace(path: str | Path) -> list[dict[str, Any]]:
    steps = []
    for i, line in enumerate(Path(path).read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            steps.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{i}: invalid JSON: {exc}") from None
    return steps


def tool_calls(steps: list[dict[str, Any]]) -> list[str]:
    return [s.get("tool", "") for s in steps if s.get("type") == "tool_call"]


def _is_subsequence(needle: list[str], haystack: list[str]) -> bool:
    it = iter(haystack)
    return all(item in it for item in needle)


def check_trace(steps: list[dict[str, Any]], policy: TracePolicy) -> list[Violation]:
    violations: list[Violation] = []
    tools = tool_calls(steps)

    if policy.max_steps is not None and len(steps) > policy.max_steps:
        violations.append(
            Violation("max_steps", f"trace has {len(steps)} steps > limit {policy.max_steps}")
        )

    if policy.max_cost_usd is not None:
        total = sum(float(s.get("cost_usd", 0.0)) for s in steps)
        if total > policy.max_cost_usd:
            violations.append(
                Violation(
                    "max_cost_usd",
                    f"trace cost ${total:.4f} > budget ${policy.max_cost_usd:.4f}",
                )
            )

    for tool in policy.forbidden_tools:
        if tool in tools:
            violations.append(Violation("forbidden_tools", f"forbidden tool {tool!r} was called"))

    for tool in policy.required_tools:
        if tool not in tools:
            violations.append(
                Violation("required_tools", f"required tool {tool!r} was never called")
            )

    if policy.required_order and not _is_subsequence(policy.required_order, tools):
        violations.append(
            Violation(
                "required_order",
                f"tool calls {tools} do not contain {policy.required_order} in order",
            )
        )

    if policy.max_tool_repeats is not None:
        for tool, count in Counter(tools).items():
            if count > policy.max_tool_repeats:
                violations.append(
                    Violation(
                        "max_tool_repeats",
                        f"tool {tool!r} called {count}x > limit {policy.max_tool_repeats} "
                        "(possible loop)",
                    )
                )

    return violations
