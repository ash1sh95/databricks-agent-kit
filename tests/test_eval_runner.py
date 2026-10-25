from pathlib import Path

from agent_kit import EvalCase, EvalRunner, load_dataset, score_case
from examples.workspace_insight_agent import build_agent

ROOT = Path(__file__).parent.parent


def test_score_case_checks_tool_and_content():
    case = EvalCase("x", "q", expected_tool="query_billing", expected_contains=["$"])
    assert score_case(case, "total $5", ["query_billing"]).passed
    bad_tool = score_case(case, "total $5", [])
    assert not bad_tool.passed and bad_tool.reasons
    bad_text = score_case(case, "no money mentioned", ["query_billing"])
    assert not bad_text.passed


def test_runner_with_simple_cases():
    cases = [
        EvalCase("billing", "What is our total billing cost?", "query_billing", ["$"]),
        EvalCase("jobs", "Which jobs failed?", "query_failed_jobs", ["FAILED"]),
    ]
    report = EvalRunner(build_agent).run(cases)
    assert report.total == 2
    assert report.pass_rate == 1.0
    assert "Pass rate: 2/2" in report.summary()


def test_shipped_dataset_loads_and_passes():
    cases = load_dataset(ROOT / "evals" / "dataset.jsonl")
    assert len(cases) >= 8
    report = EvalRunner(build_agent).run(cases)
    assert report.pass_rate == 1.0, report.summary()
