"""llm-canary command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from llm_canary import __version__
from llm_canary.baseline import (
    DEFAULT_BASELINE,
    check_drift,
    load_baseline,
    save_baseline,
)
from llm_canary.config import load_policy, load_suite
from llm_canary.report import (
    console_report,
    drift_report,
    junit_report,
    markdown_report,
    violations_report,
)
from llm_canary.runner import build_context, run_suite
from llm_canary.trace import check_trace, load_trace

EXAMPLE_SUITE = """\
name: smoke
providers:
  - name: echo          # offline; swap for openai/anthropic when keys are available
judge:
  name: fixture
  options:
    default: '{"score": 1.0, "reason": "offline judge stub"}'
cases:
  - name: greeting
    prompt: "Reply with a short greeting containing the word hello"
    assertions:
      - type: contains
        value: hello
        case_insensitive: true
      - type: max_cost_usd
        value: 0.01
"""


def cmd_run(args: argparse.Namespace) -> int:
    suite = load_suite(args.suite)
    result = run_suite(suite)
    print(console_report(result, verbose=args.verbose))
    if args.junit:
        junit_report(result, args.junit)
        print(f"junit report written to {args.junit}")
    if args.md:
        Path(args.md).write_text(markdown_report(result))
        print(f"markdown summary written to {args.md}")
    return 0 if result.passed else 1


def cmd_record(args: argparse.Namespace) -> int:
    suite = load_suite(args.suite)
    result = run_suite(suite)
    save_baseline(result, args.baseline)
    print(f"baseline for {len(result.results)} case(s) written to {args.baseline}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    suite = load_suite(args.suite)
    try:
        baseline = load_baseline(args.baseline)
    except FileNotFoundError:
        print(f"no baseline at {args.baseline} — run `llm-canary record` first", file=sys.stderr)
        return 2
    result = run_suite(suite)
    drifts = check_drift(
        result,
        baseline,
        build_context(suite),
        similarity_threshold=args.similarity_threshold,
        cost_drift_ratio=args.cost_drift,
    )
    print(drift_report(drifts))
    return 0 if not drifts else 1


def cmd_trace(args: argparse.Namespace) -> int:
    steps = load_trace(args.trace)
    policy = load_policy(args.policy)
    violations = check_trace(steps, policy)
    print(violations_report(violations))
    return 0 if not violations else 1


def cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.path)
    if target.exists():
        print(f"{target} already exists, not overwriting", file=sys.stderr)
        return 2
    target.write_text(EXAMPLE_SUITE)
    print(f"wrote starter suite to {target} — try: llm-canary run {target}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="llm-canary",
        description="Regression canary for LLM prompts and agent traces.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="run a suite and gate on assertion failures")
    p_run.add_argument("suite", help="path to suite YAML")
    p_run.add_argument("--junit", help="write a JUnit XML report")
    p_run.add_argument("--md", help="write a Markdown summary (e.g. for a PR comment)")
    p_run.add_argument("-v", "--verbose", action="store_true")
    p_run.set_defaults(func=cmd_run)

    p_record = sub.add_parser("record", help="snapshot current outputs as the baseline")
    p_record.add_argument("suite")
    p_record.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    p_record.set_defaults(func=cmd_record)

    p_check = sub.add_parser("check", help="rerun and gate on drift vs the baseline")
    p_check.add_argument("suite")
    p_check.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    p_check.add_argument("--similarity-threshold", type=float, default=0.8)
    p_check.add_argument("--cost-drift", type=float, default=0.2)
    p_check.set_defaults(func=cmd_check)

    p_trace = sub.add_parser("trace", help="check an agent trace (JSONL) against a policy")
    p_trace.add_argument("trace", help="path to trace JSONL")
    p_trace.add_argument("--policy", required=True, help="path to policy YAML")
    p_trace.set_defaults(func=cmd_trace)

    p_init = sub.add_parser("init", help="write a starter suite")
    p_init.add_argument("path", nargs="?", default="canary.yaml")
    p_init.set_defaults(func=cmd_init)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
