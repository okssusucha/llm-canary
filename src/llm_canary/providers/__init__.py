"""Provider registry."""

from __future__ import annotations

from llm_canary.config import ProviderSpec
from llm_canary.providers.base import Completion, Provider
from llm_canary.providers.integration import CommandProvider, HttpProvider
from llm_canary.providers.offline import EchoProvider, FixtureProvider
from llm_canary.providers.remote import AnthropicProvider, OpenAIProvider

REGISTRY: dict[str, type[Provider]] = {
    "echo": EchoProvider,
    "fixture": FixtureProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "command": CommandProvider,
    "http": HttpProvider,
}


def build_provider(spec: ProviderSpec) -> Provider:
    try:
        cls = REGISTRY[spec.name]
    except KeyError:
        known = ", ".join(sorted(REGISTRY))
        raise ValueError(f"unknown provider {spec.name!r} (known: {known})") from None
    return cls(spec)


__all__ = ["Completion", "Provider", "build_provider", "REGISTRY"]
