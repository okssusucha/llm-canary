from pathlib import Path

import yaml

from llm_canary.cli import main

SUITE = """\
name: cli-suite
providers:
  - name: echo
cases:
  - name: greet
    prompt: "hello there"
    assertions:
      - type: contains
        value: hello
"""

FAILING_SUITE = SUITE.replace("value: hello", "value: absent-text")


def write(tmp_path: Path, name: str, content: str) -> str:
    path = tmp_path / name
    path.write_text(content)
    return str(path)


def test_run_green_suite_exits_zero(tmp_path, capsys):
    assert main(["run", write(tmp_path, "s.yaml", SUITE)]) == 0
    out = capsys.readouterr().out
    assert "1 passed, 0 failed" in out


def test_run_failing_suite_exits_one(tmp_path):
    assert main(["run", write(tmp_path, "s.yaml", FAILING_SUITE)]) == 1


def test_run_writes_junit_and_markdown(tmp_path):
    junit = tmp_path / "junit.xml"
    md = tmp_path / "summary.md"
    code = main(
        ["run", write(tmp_path, "s.yaml", SUITE), "--junit", str(junit), "--md", str(md)]
    )
    assert code == 0
    assert junit.exists() and md.exists()
    assert "llm-canary" in md.read_text()


def test_record_then_check(tmp_path):
    suite = write(tmp_path, "s.yaml", SUITE)
    baseline = str(tmp_path / "baseline.json")
    assert main(["record", suite, "--baseline", baseline]) == 0
    assert main(["check", suite, "--baseline", baseline]) == 0


def test_check_without_baseline_exits_two(tmp_path):
    assert main(["check", write(tmp_path, "s.yaml", SUITE), "--baseline", "/nonexistent"]) == 2


def test_trace_command(tmp_path, capsys):
    trace = write(tmp_path, "t.jsonl", '{"type": "tool_call", "tool": "search"}\n')
    ok_policy = write(tmp_path, "ok.yaml", "max_steps: 5\n")
    bad_policy = write(tmp_path, "bad.yaml", "forbidden_tools: [search]\n")
    assert main(["trace", trace, "--policy", ok_policy]) == 0
    assert main(["trace", trace, "--policy", bad_policy]) == 1
    assert "forbidden" in capsys.readouterr().out


def test_init_writes_runnable_suite(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["init"]) == 0
    assert main(["init"]) == 2  # refuses to overwrite
    assert main(["run", "canary.yaml"]) == 0


def test_bundled_example_suite_passes():
    example = Path(__file__).parent.parent / "canary.example.yaml"
    assert yaml.safe_load(example.read_text())["name"] == "support-bot"
    assert main(["run", str(example)]) == 0
