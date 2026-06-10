"""Deterministic assertions: content, structure, latency, cost."""

from __future__ import annotations

import json
import re

import jsonschema

from llm_canary.config import AssertionSpec
from llm_canary.providers.base import Completion
from llm_canary.runner_context import RunContext

Result = tuple[bool, str]


def check_contains(spec: AssertionSpec, c: Completion, ctx: RunContext) -> Result:
    needle = str(spec.value)
    haystack = c.text
    if spec.param("case_insensitive", False):
        needle, haystack = needle.lower(), haystack.lower()
    ok = needle in haystack
    return ok, "" if ok else f"output does not contain {needle!r}"


def check_not_contains(spec: AssertionSpec, c: Completion, ctx: RunContext) -> Result:
    needle = str(spec.value)
    haystack = c.text
    if spec.param("case_insensitive", False):
        needle, haystack = needle.lower(), haystack.lower()
    ok = needle not in haystack
    return ok, "" if ok else f"output contains forbidden text {needle!r}"


def check_regex(spec: AssertionSpec, c: Completion, ctx: RunContext) -> Result:
    pattern = str(spec.value)
    ok = re.search(pattern, c.text, re.DOTALL) is not None
    return ok, "" if ok else f"output does not match /{pattern}/"


def check_equals(spec: AssertionSpec, c: Completion, ctx: RunContext) -> Result:
    expected = str(spec.value)
    ok = c.text.strip() == expected.strip()
    return ok, "" if ok else f"output != expected (got {c.text[:120]!r})"


def _parse_json(text: str):
    """Parse JSON wrapped in prose or ``` fences — models love both."""
    fenced = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1).strip())
    start = re.search(r"[{\[]", text)
    candidate = (text[start.start() :] if start else text).strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        # tolerate trailing prose after the JSON ("... } Hope that helps!")
        obj, _ = json.JSONDecoder().raw_decode(candidate)
        return obj


def check_json_valid(spec: AssertionSpec, c: Completion, ctx: RunContext) -> Result:
    try:
        _parse_json(c.text)
        return True, ""
    except json.JSONDecodeError as exc:
        return False, f"output is not valid JSON: {exc}"


def check_json_schema(spec: AssertionSpec, c: Completion, ctx: RunContext) -> Result:
    try:
        data = _parse_json(c.text)
    except json.JSONDecodeError as exc:
        return False, f"output is not valid JSON: {exc}"
    try:
        jsonschema.validate(data, spec.value)
        return True, ""
    except jsonschema.ValidationError as exc:
        return False, f"schema violation: {exc.message}"


def check_max_latency(spec: AssertionSpec, c: Completion, ctx: RunContext) -> Result:
    limit = float(spec.value)
    ok = c.latency_ms <= limit
    return ok, "" if ok else f"latency {c.latency_ms:.0f}ms > limit {limit:.0f}ms"


def check_max_cost(spec: AssertionSpec, c: Completion, ctx: RunContext) -> Result:
    limit = float(spec.value)
    ok = c.cost_usd <= limit
    return ok, "" if ok else f"cost ${c.cost_usd:.6f} > limit ${limit:.6f}"


def check_max_output_tokens(spec: AssertionSpec, c: Completion, ctx: RunContext) -> Result:
    limit = int(spec.value)
    ok = c.output_tokens <= limit
    return ok, "" if ok else f"output {c.output_tokens} tokens > limit {limit}"
