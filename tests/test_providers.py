import pytest
import respx
from httpx import Response

from llm_canary.config import ProviderSpec
from llm_canary.providers import build_provider
from llm_canary.providers.remote import AnthropicProvider, OpenAIProvider


def test_echo_returns_prompt_with_zero_cost():
    provider = build_provider(ProviderSpec(name="echo"))
    completion = provider.complete("ping")
    assert completion.text == "ping"
    assert completion.cost_usd == 0.0
    assert completion.input_tokens >= 1


def test_echo_template_option():
    provider = build_provider(ProviderSpec(name="echo", options={"template": "reply: {prompt}"}))
    assert provider.complete("hi").text == "reply: hi"


def test_fixture_matches_rules_in_order():
    provider = build_provider(
        ProviderSpec(
            name="fixture",
            options={
                "responses": [{"match": "refund", "text": "30 days"}],
                "default": "fallback",
            },
        )
    )
    assert provider.complete("Can I get a REFUND?").text == "30 days"
    assert provider.complete("unrelated").text == "fallback"


def test_remote_providers_require_keys(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        OpenAIProvider(ProviderSpec(name="openai")).complete("hi")
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        AnthropicProvider(ProviderSpec(name="anthropic")).complete("hi")


@respx.mock
def test_openai_provider_parses_response(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=Response(
            200,
            json={
                "choices": [{"message": {"content": "pong"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )
    )
    completion = OpenAIProvider(ProviderSpec(name="openai", model="gpt-4o-mini")).complete("ping")
    assert completion.text == "pong"
    assert completion.input_tokens == 10
    assert completion.cost_usd > 0


@respx.mock
def test_anthropic_provider_parses_response(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=Response(
            200,
            json={
                "content": [{"type": "text", "text": "pong"}],
                "usage": {"input_tokens": 8, "output_tokens": 4},
            },
        )
    )
    provider = AnthropicProvider(ProviderSpec(name="anthropic", model="claude-haiku-4-5"))
    completion = provider.complete("ping")
    assert completion.text == "pong"
    assert completion.output_tokens == 4
    assert completion.cost_usd > 0
