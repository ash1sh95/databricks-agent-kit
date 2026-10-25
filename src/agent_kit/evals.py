"""Evaluation: score what the agent *did*, not just what it said.

Dataset format (JSONL, one case per line)::

    {"id": "billing-total", "question": "What did we spend in total?",
     "expected_tool": "query_billing", "expected_contains": ["$"]}

A case passes when the agent used the expected tool (if one is named) and
its answer contains every expected substring (case-insensitive). That is a
deliberately simple, auditable scorer. In a workspace the same dataset runs
under MLflow's evaluation / agent evaluation tooling and the results log to
an MLflow experiment; locally (no mlflow installed) this module is the
scorer, so CI and a laptop produce numbers with zero setup.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EvalCase:
    id: str
    question: str
    expected_tool: str | None = None
    expected_contains: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> EvalCase:
        return cls(
            id=data["id"],
            question=data["question"],
            expected_tool=data.get("expected_tool"),
            expected_contains=list(data.get("expected_contains", [])),
        )


@dataclass
class CaseResult:
    case_id: str
    passed: bool
    tools_used: list[str]
    answer: str
    reasons: list[str] = field(default_factory=list)


@dataclass
class EvalReport:
    results: list[CaseResult]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    def summary(self) -> str:
        lines = [
            f"{'case':<26} {'tools':<28} result",
            "-" * 68,
        ]
        for r in self.results:
            lines.append(f"{r.case_id:<26} {','.join(r.tools_used) or '-':<28} "
                         f"{'PASS' if r.passed else 'FAIL'}")
            for reason in r.reasons:
                lines.append(f"  -> {reason}")
        lines += [
            "-" * 68,
            f"Pass rate: {self.passed}/{self.total} = {self.pass_rate:.1%}",
        ]
        return "\n".join(lines)


def load_dataset(path: str | Path) -> list[EvalCase]:
    cases = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            cases.append(EvalCase.from_dict(json.loads(line)))
    return cases


def score_case(case: EvalCase, answer: str, tools_used: list[str]) -> CaseResult:
    reasons: list[str] = []
    if case.expected_tool and case.expected_tool not in tools_used:
        reasons.append(f"expected tool {case.expected_tool}, used {tools_used or 'none'}")
    lowered = answer.lower()
    for needle in case.expected_contains:
        if needle.lower() not in lowered:
            reasons.append(f"answer missing {needle!r}")
    return CaseResult(case.id, not reasons, tools_used, answer, reasons)


class EvalRunner:
    """Run cases against agents built by ``agent_factory`` (fresh agent per
    case, so tool state never leaks between cases)."""

    def __init__(self, agent_factory: Callable[[], object]) -> None:
        self.agent_factory = agent_factory

    def run(self, cases: list[EvalCase]) -> EvalReport:
        results = []
        for case in cases:
            agent = self.agent_factory()
            result = agent.run(case.question)  # agent_kit.agent.Agent
            results.append(score_case(case, result.answer, result.tools_used))
        return EvalReport(results)

    def run_and_log_mlflow(self, cases: list[EvalCase], experiment: str) -> EvalReport:
        """Run, then log pass-rate metrics to MLflow if it is installed.

        Logging is best-effort: an offline run without mlflow still returns
        the report — evals you cannot run locally do not get run at all.
        """
        report = self.run(cases)
        try:
            import mlflow  # type: ignore
        except ImportError:
            return report
        mlflow.set_experiment(experiment)
        with mlflow.start_run(run_name="agent-kit-eval"):
            mlflow.log_metric("pass_rate", report.pass_rate)
            mlflow.log_metric("passed", report.passed)
            mlflow.log_metric("total", report.total)
            for r in report.results:
                mlflow.log_metric(f"case_{r.case_id}", 1.0 if r.passed else 0.0)
        return report
