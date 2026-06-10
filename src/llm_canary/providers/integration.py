"""Universal integration providers: connect ANY bot to llm-canary.

``command`` runs an arbitrary executable — any language, any framework.
The prompt is substituted into ``{prompt}`` placeholders in the command's
arguments, or piped to stdin when no placeholder is present. stdout is the
reply. The command runs without a shell (args are split with shlex), so
YAML stays readable and quoting stays sane.

``http`` posts the prompt to any REST endpoint. ``{prompt}`` placeholders
are substituted recursively into the body/params/url, and the reply is
extracted from the response JSON via a dot path (``response_path``), or the
raw body is used when no path is given.

Cost is unknown for both (your app pays its own bills), so it is reported
as 0 — combine with trace policies if you need cost gates for agents.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import time
import urllib.parse
from typing import Any

import httpx

from llm_canary.pricing import estimate_tokens
from llm_canary.providers.base import Completion, Provider


class CommandProvider(Provider):
    """options: cmd (required, ``{prompt}`` placeholder optional), timeout (seconds)."""

    def complete(self, prompt: str) -> Completion:
        cmd = self.spec.options.get("cmd")
        if not cmd:
            raise ValueError("command provider requires options.cmd")
        args = shlex.split(cmd)
        has_placeholder = any("{prompt}" in arg for arg in args)
        if has_placeholder:
            args = [arg.replace("{prompt}", prompt) for arg in args]
        timeout = float(self.spec.options.get("timeout", 60))
        start = time.perf_counter()
        proc = subprocess.run(
            args,
            input=None if has_placeholder else prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        latency = (time.perf_counter() - start) * 1000
        if proc.returncode != 0:
            raise RuntimeError(
                f"command exited with {proc.returncode}: {proc.stderr.strip()[:200]}"
            )
        text = proc.stdout.strip()
        return Completion(
            text=text,
            input_tokens=estimate_tokens(prompt),
            output_tokens=estimate_tokens(text),
            cost_usd=0.0,
            latency_ms=latency,
        )


def _substitute(value: Any, prompt: str) -> Any:
    if isinstance(value, str):
        return value.replace("{prompt}", prompt)
    if isinstance(value, dict):
        return {k: _substitute(v, prompt) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute(v, prompt) for v in value]
    return value


def _extract(data: Any, path: str) -> str:
    current = data
    for part in path.split("."):
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict):
            current = current[part]
        else:
            raise KeyError(part)
    return current if isinstance(current, str) else str(current)


class HttpProvider(Provider):
    """options: url (required), method, headers, body, params, response_path, timeout."""

    def complete(self, prompt: str) -> Completion:
        options = self.spec.options
        url = options.get("url")
        if not url:
            raise ValueError("http provider requires options.url")
        url = url.replace("{prompt}", urllib.parse.quote(prompt))
        method = options.get("method", "POST").upper()
        body = _substitute(options.get("body"), prompt)
        params = _substitute(options.get("params"), prompt)
        headers = options.get("headers")
        if headers:
            # expand ${ENV_VAR} so tokens stay out of the suite YAML
            headers = {k: os.path.expandvars(v) for k, v in headers.items()}
        start = time.perf_counter()
        resp = httpx.request(
            method,
            url,
            headers=headers,
            json=body if isinstance(body, (dict, list)) else None,
            content=body if isinstance(body, str) else None,
            params=params,
            timeout=float(options.get("timeout", 60)),
        )
        resp.raise_for_status()
        latency = (time.perf_counter() - start) * 1000
        path = options.get("response_path")
        if path:
            try:
                text = _extract(resp.json(), path)
            except (KeyError, IndexError, ValueError) as exc:
                raise RuntimeError(
                    f"response_path {path!r} not found in response: {resp.text[:200]}"
                ) from exc
        else:
            text = resp.text
        return Completion(
            text=text,
            input_tokens=estimate_tokens(prompt),
            output_tokens=estimate_tokens(text),
            cost_usd=0.0,
            latency_ms=latency,
        )
