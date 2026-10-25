# Changelog

## v0.1.0 — 2026-10-25

Initial release.

- Tool registry with Unity Catalog-style specs: one declaration drives the
  model-facing schema, a local executor, and generated `CREATE FUNCTION`
  DDL; Databricks UC executor as an interface stub.
- Agent loop (plain-Python reference implementation) with an optional
  LangGraph wrapper and a `pre_tool_hook` governance seam that composes
  with agent-control-plane.
- Model clients: deterministic MockModel for offline work and tests, and a
  Model Serving / Foundation Model API client for workspaces.
- RAG: chunking + dependency-free BM25 retriever; Vector Search retriever
  as an interface stub.
- Evals: JSONL dataset format, local scorer/runner with per-case reasons,
  optional MLflow metric logging; 8-case dataset for the example agent.
- Example: workspace-insight agent over synthetic system-table-like data
  (billing, job runs) plus team docs, with a gated variant example.
- Databricks: deploy notebook (widgets, MLflow + optional Delta results),
  Asset Bundle skeleton, and a 15-minute deployment guide.
- Suite documentation: how build → govern → observe → evaluate composes
  across agent-control-plane, dspy-observability-dashboard and
  databricks-insight-agent.
