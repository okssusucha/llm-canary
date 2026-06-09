"""Remote providers (OpenAI / Anthropic chat completions).

Only used when a suite explicitly selects them; everything else in
llm-canary runs offline. API keys come from the environment.
"""

from __future__ import annotations

import os
import time

import httpx

from llm_canary.pricing import estimate_cost
from llm_canary.providers.base import Completion, Provider

TIMEOUT = 60.0


class OpenAIProvider(Provider):
    def complete(self, prompt: str) -> Completion:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set (use the echo provider for offline runs)")
        base = self.spec.options.get("base_url", "https://api.openai.com/v1")
        model = self.spec.model or "gpt-4o-mini"
        start = time.perf_counter()
        resp = httpx.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}]},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        latency = (time.perf_counter() - start) * 1000
        data = resp.json()
        usage = data.get("usage", {})
        in_tok = usage.get("prompt_tokens", 0)
        out_tok = usage.get("completion_tokens", 0)
        return Completion(
            text=data["choices"][0]["message"]["content"] or "",
            input_tokens=in_tok,
            output_tokens=out_tok,
            cost_usd=estimate_cost(model, in_tok, out_tok),
            latency_ms=latency,
        )


class AnthropicProvider(Provider):
    def complete(self, prompt: str) -> Completion:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set (use the echo provider for offline runs)"
            )
        base = self.spec.options.get("base_url", "https://api.anthropic.com")
        model = self.spec.model or "claude-haiku-4-5"
        start = time.perf_counter()
        resp = httpx.post(
            f"{base}/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
            json={
                "model": model,
                "max_tokens": self.spec.options.get("max_tokens", 1024),
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        latency = (time.perf_counter() - start) * 1000
        data = resp.json()
        usage = data.get("usage", {})
        in_tok = usage.get("input_tokens", 0)
        out_tok = usage.get("output_tokens", 0)
        text = "".join(b.get("text", "") for b in data.get("content", []))
        return Completion(
            text=text,
            input_tokens=in_tok,
            output_tokens=out_tok,
            cost_usd=estimate_cost(model, in_tok, out_tok),
            latency_ms=latency,
        )
