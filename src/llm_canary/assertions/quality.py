"""Quality assertions: semantic similarity and LLM-as-judge."""

from __future__ import annotations

import json
import re

from llm_canary.config import AssertionSpec
from llm_canary.providers.base import Completion
from llm_canary.runner_context import RunContext
from llm_canary.semantic import similarity

Result = tuple[bool, str]

JUDGE_PROMPT = """\
You are a strict, impartial evaluator.

Criteria: {criteria}

Candidate response:
---
{output}
---

Score how well the candidate satisfies the criteria.
Respond with ONLY a JSON object: {{"score": <float 0.0-1.0>, "reason": "<one sentence>"}}"""


def check_similarity(spec: AssertionSpec, c: Completion, ctx: RunContext) -> Result:
    reference = str(spec.value)
    threshold = spec.threshold if spec.threshold is not None else 0.8
    score = similarity(ctx.embedder, c.text, reference)
    ok = score >= threshold
    return ok, "" if ok else f"similarity {score:.3f} < threshold {threshold:.3f}"


def check_judge(spec: AssertionSpec, c: Completion, ctx: RunContext) -> Result:
    if ctx.judge_provider is None:
        return False, "judge assertion used but no `judge:` provider configured in the suite"
    threshold = spec.threshold if spec.threshold is not None else 0.7
    prompt = JUDGE_PROMPT.format(criteria=str(spec.value), output=c.text)
    verdict = ctx.judge_provider.complete(prompt)
    match = re.search(r"\{.*\}", verdict.text, re.DOTALL)
    if not match:
        return False, f"judge returned no JSON verdict: {verdict.text[:120]!r}"
    try:
        data = json.loads(match.group(0))
        score = float(data["score"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return False, f"unparseable judge verdict: {exc}"
    reason = data.get("reason", "")
    ok = score >= threshold
    return ok, "" if ok else f"judge score {score:.2f} < threshold {threshold:.2f} ({reason})"
