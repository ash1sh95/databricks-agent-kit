# Patterns guide — how the kit maps to Databricks

Names below are Databricks platform concepts as documented in the
Databricks docs (docs.databricks.com). The kit takes no position the docs
don't support; where behaviour varies by workspace configuration, the guide
says so.

## Unity Catalog functions as tools

Declare each tool once as data (name, description, typed parameters) — the
same information a Unity Catalog function carries. From that one spec the
kit derives:

- the function schema handed to the model,
- the local handler used in dev/CI,
- `CREATE FUNCTION` DDL (`ToolSpec.to_uc_ddl`) for persisting the tool in
  Unity Catalog, where permissions are governed like any other UC object.

Rule of thumb: **if a tool crosses a trust boundary, it should be a UC
function**, because UC gives you one governed registry instead of tool
code copied into every agent repo.

## Model Serving + AI Gateway

Agents call a model through a Model Serving endpoint or the Foundation
Model APIs. In production, serve/govern that endpoint through **AI
Gateway** capabilities on Model Serving — usage tracking, inference
tables, guardrails and rate limiting are configured on the endpoint, not
in agent code. The kit's `ModelServingClient` therefore stays dumb: swap
endpoint names via config, never branch on governance in the agent.

## MLflow tracing and evaluation

- **Tracing**: MLflow's tracing (built on OpenTelemetry concepts) records
  the spans of an agent run — model calls, tool calls, retrieval. The kit's
  `AgentResult.trace` is the offline stand-in for the same idea: an ordered
  event list you can print in CI and log in a workspace.
- **Evaluation**: keep a versioned dataset of questions with expected
  tools/outcomes, run it on every change, and log metrics to an MLflow
  experiment (`EvalRunner.run_and_log_mlflow`). Databricks' agent
  evaluation tooling (Mosaic AI Agent Evaluation) builds on the same
  MLflow foundation for richer, judge-based scoring in a workspace; the
  kit's local scorer is the deterministic floor beneath it, not a
  replacement for it.

## Vector Search for RAG

For workspace retrieval, create a Vector Search endpoint and a Delta Sync
index over a Unity Catalog table of chunks/embeddings, then query it for
similarity search. The kit mirrors that shape with
`DatabricksVectorSearchRetriever` (stub) and ships a BM25 retriever as the
transparent baseline: evaluate retrieval changes against the baseline
before assuming an embedding model is the problem.

## Agent Framework / LangGraph

The Mosaic AI Agent Framework is Databricks' toolchain for building,
deploying and evaluating agents (including LangGraph-based ones) with
MLflow integration. The kit's `build_langgraph_agent` wraps the same
registry/executor/model trio in a small StateGraph so a project started
here can move onto that toolchain without redesigning its tools or evals.

## Asset Bundles for deployment

Jobs, pipelines and (in current schema versions) apps are deployed
repeatably with Databricks Asset Bundles (`databricks.yml`). The kit's
bundle skeleton ships the eval notebook as a job — evaluation as a
scheduled, deployable artifact, not a manual notebook habit.
