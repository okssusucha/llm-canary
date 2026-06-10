"""Tests for v0.4.0 features: brace-safe vars, prose-tolerant JSON, matrix,
parallel execution, system prompts, server auth, validate command."""

import json

import respx
from fastapi.testclient import TestClient
from httpx import Response

from llm_canary.assertions import run_assertion
from llm_canary.cli import main
from llm_canary.config import AssertionSpec, CaseSpec, ProviderSpec, SuiteSpec
from llm_canary.providers.base import Completion
from llm_canary.providers.remote import AnthropicProvider, OpenAIProvider
from llm_canary.runner import expand_cases, run_suite
from llm_canary.runner_context import RunContext
from llm_canary.server import create_app


def test_prompt_with_literal_braces_survives_var_rendering():
    case = CaseSpec(
        name="c",
        prompt='Reply as JSON like {"ok": true}. Question: {q}',
        vars={"q": "hi"},
    )
    assert case.rendered_prompt() == 'Reply as JSON like {"ok": true}. Question: hi'


def test_json_valid_tolerates_trailing_prose():
    completion = Completion(text='Here you go: {"a": 1} Hope that helps!')
    result = run_assertion(AssertionSpec(type="json_valid"), completion, RunContext())
    assert result.passed


def test_matrix_expands_cartesian_product():
    case = CaseSpec(
        name="greet",
        prompt="say {word} in {lang}",
        matrix={"word": ["hello", "bye"], "lang": ["ja", "ko"]},
    )
    expanded = expand_cases([case])
    assert [c.name for c in expanded] == [
        "greet[hello,ja]",
        "greet[hello,ko]",
        "greet[bye,ja]",
        "greet[bye,ko]",
    ]
    assert expanded[0].rendered_prompt() == "say hello in ja"


def test_matrix_cases_run_in_suite():
    suite = SuiteSpec(
        name="m",
        providers=[ProviderSpec(name="echo")],
        cases=[
            CaseSpec(
                name="c",
                prompt="{x}",
                matrix={"x": ["a", "b"]},
                assertions=[AssertionSpec(type="regex", value="^[ab]$")],
            )
        ],
    )
    result = run_suite(suite)
    assert len(result.results) == 2
    assert result.passed


def test_parallel_run_preserves_order_and_results():
    suite = SuiteSpec(
        name="p",
        providers=[ProviderSpec(name="echo")],
        cases=[
            CaseSpec(
                name=f"c{i}",
                prompt=f"prompt-{i}",
                assertions=[AssertionSpec(type="contains", value=f"prompt-{i}")],
            )
            for i in range(8)
        ],
    )
    result = run_suite(suite, max_workers=4)
    assert result.passed
    assert [r.case for r in result.results] == [f"c{i}" for i in range(8)]


@respx.mock
def test_openai_system_prompt_inline(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    route = respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=Response(
            200, json={"choices": [{"message": {"content": "x"}}], "usage": {}}
        )
    )
    spec = ProviderSpec(name="openai", options={"system_prompt": "You are a support bot."})
    OpenAIProvider(spec).complete("hi")
    sent = json.loads(route.calls.last.request.content)
    assert sent["messages"][0] == {"role": "system", "content": "You are a support bot."}


@respx.mock
def test_anthropic_system_prompt_from_file(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    prompt_file = tmp_path / "system.txt"
    prompt_file.write_text("Be terse.")
    route = respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=Response(200, json={"content": [], "usage": {}})
    )
    spec = ProviderSpec(name="anthropic", options={"system_prompt_file": str(prompt_file)})
    AnthropicProvider(spec).complete("hi")
    sent = json.loads(route.calls.last.request.content)
    assert sent["system"] == "Be terse."


SUITE = {
    "name": "s",
    "providers": [{"name": "echo"}],
    "cases": [{"name": "c", "prompt": "hello"}],
}


def test_server_token_auth(tmp_path):
    client = TestClient(create_app(str(tmp_path / "db"), token="sekrit"))
    assert client.get("/healthz").status_code == 200  # liveness stays open
    assert client.post("/api/runs", json=SUITE).status_code == 401
    assert client.get("/").status_code == 401
    ok = client.post("/api/runs", json=SUITE, headers={"Authorization": "Bearer sekrit"})
    assert ok.status_code == 200


def test_server_without_token_is_open(tmp_path):
    client = TestClient(create_app(str(tmp_path / "db")))
    assert client.post("/api/runs", json=SUITE).status_code == 200


def write_suite(tmp_path, content):
    path = tmp_path / "suite.yaml"
    path.write_text(content)
    return str(path)


def test_validate_accepts_good_suite(tmp_path, capsys):
    path = write_suite(
        tmp_path,
        "name: ok\nproviders: [{name: echo}]\n"
        "cases: [{name: c, prompt: hi, assertions: [{type: contains, value: h}]}]\n",
    )
    assert main(["validate", path]) == 0
    assert "suite OK" in capsys.readouterr().out


def test_validate_flags_unknown_types_and_missing_judge(tmp_path, capsys):
    path = write_suite(
        tmp_path,
        "name: bad\nproviders: [{name: nope}]\n"
        "cases: [{name: c, prompt: hi, assertions: [{type: wat}, {type: judge, value: x}]}]\n",
    )
    assert main(["validate", path]) == 1
    err = capsys.readouterr().err
    assert "unknown provider 'nope'" in err
    assert "unknown assertion type 'wat'" in err
    assert "no judge provider" in err


def test_run_json_output(tmp_path, capsys):
    path = write_suite(
        tmp_path,
        "name: j\nproviders: [{name: echo}]\ncases: [{name: c, prompt: hi}]\n",
    )
    assert main(["run", path, "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["suite"] == "j"
    assert data["results"][0]["output"] == "hi"


def test_run_max_workers_cli(tmp_path):
    path = write_suite(
        tmp_path,
        "name: w\nproviders: [{name: echo}]\ncases: [{name: c, prompt: hi}]\n",
    )
    assert main(["run", path, "--max-workers", "4"]) == 0
