"""Offline providers: the default path that needs no API key.

``echo`` returns the prompt (optionally through a template) — useful for
wiring up suites and exercising assertions deterministically.

``fixture`` maps prompts to canned responses with regex rules — useful for
demoing real pass/fail behavior and as an offline LLM-as-judge.
"""

from __future__ import annotations

import re
import time

from llm_canary.pricing import estimate_tokens
from llm_canary.providers.base import Completion, Provider


class EchoProvider(Provider):
    def complete(self, prompt: str) -> Completion:
        start = time.perf_counter()
        template = self.spec.options.get("template", "{prompt}")
        text = template.format(prompt=prompt)
        latency = (time.perf_counter() - start) * 1000
        return Completion(
            text=text,
            input_tokens=estimate_tokens(prompt),
            output_tokens=estimate_tokens(text),
            cost_usd=0.0,
            latency_ms=latency,
        )


class FixtureProvider(Provider):
    """options.responses: list of {match: <regex>, text: <reply>}; options.default: fallback."""

    def complete(self, prompt: str) -> Completion:
        start = time.perf_counter()
        text = None
        for rule in self.spec.options.get("responses", []):
            if re.search(rule["match"], prompt, re.IGNORECASE | re.DOTALL):
                text = rule["text"]
                break
        if text is None:
            text = self.spec.options.get("default")
        if text is None:
            raise ValueError(f"fixture provider has no rule matching prompt: {prompt[:80]!r}")
        latency = (time.perf_counter() - start) * 1000
        return Completion(
            text=text,
            input_tokens=estimate_tokens(prompt),
            output_tokens=estimate_tokens(text),
            cost_usd=0.0,
            latency_ms=latency,
        )
