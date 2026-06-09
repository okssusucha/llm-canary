import pytest

from llm_canary.config import TracePolicy
from llm_canary.trace import check_trace, load_trace

TRACE = [
    {"type": "message", "role": "user", "content": "go"},
    {"type": "tool_call", "tool": "search", "cost_usd": 0.002},
    {"type": "tool_call", "tool": "summarize", "cost_usd": 0.004},
    {"type": "tool_call", "tool": "post_slack", "cost_usd": 0.001},
]


def rules(violations):
    return {v.rule for v in violations}


def test_clean_trace_passes():
    policy = TracePolicy(
        max_steps=10,
        max_cost_usd=0.05,
        forbidden_tools=["delete_db"],
        required_tools=["search"],
        required_order=["search", "post_slack"],
        max_tool_repeats=3,
    )
    assert check_trace(TRACE, policy) == []


def test_max_steps_and_cost():
    assert rules(check_trace(TRACE, TracePolicy(max_steps=2))) == {"max_steps"}
    assert rules(check_trace(TRACE, TracePolicy(max_cost_usd=0.001))) == {"max_cost_usd"}


def test_forbidden_and_required_tools():
    assert rules(check_trace(TRACE, TracePolicy(forbidden_tools=["summarize"]))) == {
        "forbidden_tools"
    }
    assert rules(check_trace(TRACE, TracePolicy(required_tools=["send_email"]))) == {
        "required_tools"
    }


def test_required_order_is_a_subsequence():
    assert check_trace(TRACE, TracePolicy(required_order=["search", "summarize"])) == []
    assert rules(check_trace(TRACE, TracePolicy(required_order=["post_slack", "search"]))) == {
        "required_order"
    }


def test_max_tool_repeats_catches_loops():
    looping = [{"type": "tool_call", "tool": "search"} for _ in range(5)]
    violations = check_trace(looping, TracePolicy(max_tool_repeats=3))
    assert rules(violations) == {"max_tool_repeats"}
    assert "loop" in violations[0].message


def test_load_trace_jsonl(tmp_path):
    path = tmp_path / "trace.jsonl"
    path.write_text('{"type": "tool_call", "tool": "a"}\n\n{"type": "message"}\n')
    steps = load_trace(path)
    assert len(steps) == 2
    assert steps[0]["tool"] == "a"


def test_load_trace_rejects_bad_json(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text("{not json}\n")
    with pytest.raises(ValueError, match="invalid JSON"):
        load_trace(path)


def test_bundled_example_trace_passes_bundled_policy():
    from pathlib import Path

    from llm_canary.config import load_policy

    root = Path(__file__).parent.parent / "examples" / "agent-trace"
    steps = load_trace(root / "trace.jsonl")
    policy = load_policy(root / "policy.yaml")
    assert check_trace(steps, policy) == []
