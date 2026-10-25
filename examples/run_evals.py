"""Run the shipped eval dataset against the workspace-insight agent.

Run:  PYTHONPATH=src:. python examples/run_evals.py
Prints a per-case table and a summary line; exits non-zero if any case fails.
In a workspace, EvalRunner.run_and_log_mlflow() logs the same run to an
MLflow experiment instead.
"""
from __future__ import annotations

import sys
from pathlib import Path

from agent_kit import EvalRunner, load_dataset
from examples.workspace_insight_agent import build_agent

DATASET = Path(__file__).parent.parent / "evals" / "dataset.jsonl"


def main() -> int:
    cases = load_dataset(DATASET)
    report = EvalRunner(build_agent).run(cases)
    print(report.summary())
    return 0 if report.pass_rate == 1.0 else 1


if __name__ == "__main__":
    sys.exit(main())
