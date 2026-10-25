"""Workspace-insight agent: a complete mini agent that runs offline.

Answers questions over synthetic, system-table-like data (billing usage and
job runs as CSV) and over team documentation (BM25 RAG), using three tools
declared as Unity Catalog-style specs. The model is the deterministic
MockModel, so this exact output reproduces in CI and on any laptop.

Run:  PYTHONPATH=src:. python examples/workspace_insight_agent.py
In a workspace you would swap MockModel for ModelServingClient, the CSV
handlers for UC functions, and BM25 for a Vector Search index — the agent
code does not change.
"""
from __future__ import annotations

import csv
from pathlib import Path

from agent_kit import (
    Agent,
    BM25Retriever,
    Document,
    MockModel,
    Parameter,
    ToolRegistry,
)

HERE = Path(__file__).parent
DATA = HERE / "data"
DOCS = HERE / "sample_docs"


def _rows(name: str) -> list[dict]:
    with open(DATA / name, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    retriever = BM25Retriever(
        [Document(p.stem, p.read_text(encoding="utf-8")) for p in sorted(DOCS.glob("*.md"))]
    )

    @registry.tool(
        "query_billing",
        "Total and per-service spend from the billing usage table (synthetic sample data).",
        parameters=[],
        returns="STRING",
    )
    def query_billing() -> str:
        rows = _rows("billing_usage.csv")
        total = sum(float(r["cost_usd"]) for r in rows)
        per_service: dict[str, float] = {}
        for r in rows:
            per_service[r["service"]] = per_service.get(r["service"], 0.0) + float(r["cost_usd"])
        breakdown = ", ".join(f"{k} ${v:,.2f}" for k, v in sorted(per_service.items()))
        return f"total spend ${total:,.2f} across {len(rows)} usage rows ({breakdown})"

    @registry.tool(
        "query_failed_jobs",
        "List jobs whose latest run failed or timed out, from the job runs table.",
        parameters=[],
        returns="STRING",
    )
    def query_failed_jobs() -> str:
        bad = [r for r in _rows("job_runs.csv") if r["status"] in {"FAILED", "TIMEOUT"}]
        listing = "; ".join(
            f"{r['job_name']} ({r['status']}, {r['duration_min']} min, {r['owner_team']})" for r in bad
        )
        return f"{len(bad)} failed or timed-out jobs: {listing}"

    @registry.tool(
        "search_docs",
        "Search team documentation (retention, cost, agent patterns) for a guideline.",
        parameters=[Parameter("query", str, "Natural-language search query")],
        returns="STRING",
    )
    def search_docs(query: str) -> str:
        hits = retriever.search(query, k=1)
        if not hits:
            return "no documentation matched the query"
        chunk, score = hits[0]
        return f"from doc '{chunk.doc_id}' (bm25 {score}): {chunk.text[:300]}"

    return registry


def build_agent(**agent_kwargs) -> Agent:
    return Agent(build_registry(), model=MockModel(), **agent_kwargs)


QUESTIONS = [
    "What is our total billing cost and spend this month?",
    "Which jobs failed — show me the failing job runs?",
    "What does the documentation say about data retention policy?",
]


def main() -> None:
    agent = build_agent()
    for question in QUESTIONS:
        result = agent.run(question)
        print("=" * 72)
        for event in result.trace:
            print(event)
        print(f"ANSWER: {result.answer}\n")


if __name__ == "__main__":
    main()
