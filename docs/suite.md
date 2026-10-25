# How this kit composes with the suite

One thesis, four repos: **build → govern → observe → evaluate**
production agents on Databricks.

| Stage | Repo | What it gives you |
|---|---|---|
| **Build** | **databricks-agent-kit** (this repo) | UC-style tool registry, agent loop, Model Serving client, RAG baseline, eval harness — a runnable starting point for a new agent |
| **Govern** | [agent-control-plane](https://github.com/ash1sh95/agent-control-plane) | Judge-before-action policy gate, tool rate-limiting, duplicate-call prevention, human approvals, audit log — wraps this kit's executor via the `pre_tool_hook` seam (see `examples/gated_agent.py`) |
| **Observe** | [dspy-observability-dashboard](https://github.com/ash1sh95/dspy-observability-dashboard) | Production observability for LLM/DSPy pipelines on Databricks — MLflow tracing with cost, latency and error dashboards: what the running system actually did and cost |
| **Evaluate (in situ)** | [databricks-insight-agent](https://github.com/ash1sh95/databricks-insight-agent) | A worked example agent over Databricks system tables — the kind of agent this kit helps you build, taken further, with enterprise evaluation patterns |

## The workflow the suite is arguing for

1. **Start** a new agent from this kit: tools declared once as UC-style
   specs, a mock model locally, BM25 retrieval, and an eval dataset from
   day one — not bolted on later.
2. **Gate it** before it touches anything real: every tool call passes
   agent-control-plane's judge, budgets and approval queue. The kit's
   agent code changes by one argument (`pre_tool_hook=`).
3. **Deploy it** to a workspace with the Asset Bundle; swap the model
   client to a Model Serving endpoint behind AI Gateway and the retriever
   to Vector Search. Tools graduate into real Unity Catalog functions.
4. **Observe it** in production: MLflow traces feed the observability
   dashboards; costs and failures become visible per run, not per month.
5. **Evaluate continuously**: the eval dataset that shipped with the agent
   runs as a bundle job; every incident adds a case before it adds a fix.

Each repo stands alone — clone any one and it runs. Together they are a
reference architecture you can also *read in order* to learn how
production agent systems on Databricks fit together.
