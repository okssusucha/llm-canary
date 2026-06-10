import json

import pytest
import respx
from httpx import Response

from llm_canary.config import ProviderSpec
from llm_canary.providers.integration import CommandProvider, HttpProvider


def command(options):
    return CommandProvider(ProviderSpec(name="command", options=options))


def http(options):
    return HttpProvider(ProviderSpec(name="http", options=options))


def test_command_substitutes_prompt_into_args():
    completion = command({"cmd": "echo bot-reply: {prompt}"}).complete("hello")
    assert completion.text == "bot-reply: hello"
    assert completion.cost_usd == 0.0


def test_command_pipes_prompt_to_stdin_without_placeholder():
    assert command({"cmd": "cat"}).complete("from stdin").text == "from stdin"


def test_command_nonzero_exit_raises():
    with pytest.raises(RuntimeError, match="exited with"):
        command({"cmd": "false"}).complete("hi")


def test_command_requires_cmd_option():
    with pytest.raises(ValueError, match="options.cmd"):
        command({}).complete("hi")


@respx.mock
def test_http_posts_body_and_extracts_response_path():
    route = respx.post("http://bot.local/chat").mock(
        return_value=Response(200, json={"reply": {"text": "pong", "tokens": 3}})
    )
    completion = http(
        {
            "url": "http://bot.local/chat",
            "body": {"message": "{prompt}", "session": "ci"},
            "response_path": "reply.text",
        }
    ).complete("ping")
    assert completion.text == "pong"
    sent = json.loads(route.calls.last.request.content)
    assert sent == {"message": "ping", "session": "ci"}


@respx.mock
def test_http_response_path_supports_list_indices():
    respx.post("http://bot.local/v1").mock(
        return_value=Response(200, json={"choices": [{"message": {"content": "hi"}}]})
    )
    completion = http(
        {"url": "http://bot.local/v1", "body": {}, "response_path": "choices.0.message.content"}
    ).complete("x")
    assert completion.text == "hi"


@respx.mock
def test_http_raw_body_when_no_response_path():
    respx.get("http://bot.local/ask").mock(return_value=Response(200, text="plain reply"))
    completion = http({"url": "http://bot.local/ask", "method": "GET"}).complete("x")
    assert completion.text == "plain reply"


@respx.mock
def test_http_url_prompt_placeholder_is_encoded():
    route = respx.get("http://bot.local/ask").mock(return_value=Response(200, text="ok"))
    http({"url": "http://bot.local/ask?q={prompt}", "method": "GET"}).complete("a b")
    assert str(route.calls.last.request.url) == "http://bot.local/ask?q=a%20b"


@respx.mock
def test_http_missing_response_path_raises():
    respx.post("http://bot.local/chat").mock(return_value=Response(200, json={"other": 1}))
    with pytest.raises(RuntimeError, match="response_path"):
        http(
            {"url": "http://bot.local/chat", "body": {}, "response_path": "reply.text"}
        ).complete("x")


@respx.mock
def test_http_error_status_raises():
    respx.post("http://bot.local/chat").mock(return_value=Response(500))
    with pytest.raises(Exception, match="500"):
        http({"url": "http://bot.local/chat", "body": {}}).complete("x")


@respx.mock
def test_http_headers_expand_env_vars(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "secret123")
    route = respx.post("http://bot.local/chat").mock(return_value=Response(200, text="ok"))
    http(
        {
            "url": "http://bot.local/chat",
            "body": {},
            "headers": {"Authorization": "Bearer ${BOT_TOKEN}"},
        }
    ).complete("x")
    assert route.calls.last.request.headers["authorization"] == "Bearer secret123"


def test_http_requires_url():
    with pytest.raises(ValueError, match="options.url"):
        http({}).complete("x")
