import xml.etree.ElementTree as ET

from llm_canary.config import AssertionSpec, CaseSpec, ProviderSpec, SuiteSpec
from llm_canary.report import console_report, junit_report, markdown_report
from llm_canary.runner import run_suite


def mixed_result():
    suite = SuiteSpec(
        name="r",
        providers=[ProviderSpec(name="echo")],
        cases=[
            CaseSpec(
                name="ok",
                prompt="hello",
                assertions=[AssertionSpec(type="contains", value="hello")],
            ),
            CaseSpec(
                name="bad",
                prompt="hello",
                assertions=[AssertionSpec(type="contains", value="absent")],
            ),
        ],
    )
    return run_suite(suite)


def test_console_report_shows_failures_and_counts():
    text = console_report(mixed_result())
    assert "[PASS] echo/ok" in text
    assert "[FAIL] echo/bad" in text
    assert "1 passed, 1 failed" in text


def test_junit_report_is_valid_xml(tmp_path):
    path = tmp_path / "junit.xml"
    junit_report(mixed_result(), path)
    root = ET.parse(path).getroot()
    assert root.get("tests") == "2"
    assert root.get("failures") == "1"
    failures = root.findall("./testcase/failure")
    assert len(failures) == 1


def test_markdown_report_has_table_and_status():
    md = markdown_report(mixed_result())
    assert "| case | provider | result |" in md
    assert "❌" in md and "✅" in md
    assert "1 passed, 1 failed" in md
