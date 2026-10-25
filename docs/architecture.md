# Architecture

```mermaid
flowchart LR
    U[User / app / job] --> A[Agent loop<br/>agent_kit.agent]
    A -->|messages + tool schemas| M{Model client}
    M -->|ModelServingClient| MS[Model Serving /<br/>Foundation Model API<br/>via AI Gateway]
    M -->|MockModel| MM[Deterministic mock<br/>offline, CI]
    A -->|tool call| H[pre_tool_hook<br/>governance seam]
    H --> E{Executor}
    E -->|LocalExecutor| L[In-process handlers<br/>dev / tests]
    E -->|DatabricksUCExecutor| UC[Unity Catalog<br/>functions]
    A --> R[RAG retriever]
    R -->|BM25Retriever| B[Local chunks<br/>dev / evals]
    R -->|DatabricksVectorSearchRetriever| VS[Vector Search<br/>Delta Sync index]
    EV[EvalRunner] -->|fresh agent per case| A
    EV -->|metrics| ML[MLflow experiment<br/>optional locally]
```

## The four seams

Every production concern plugs in at a seam, without rewriting the agent:

1. **Model seam** (`ModelClient`) — mock locally, a Model Serving /
   Foundation Model API endpoint in a workspace. AI Gateway sits in front
   of the endpoint in production and is invisible to agent code.
2. **Tool seam** (`ToolRegistry` + executor) — one UC-style spec drives the
   LLM schema, the local handler and the UC `CREATE FUNCTION` DDL, so the
   three cannot drift.
3. **Retrieval seam** (`Retriever`) — BM25 baseline you can read and test;
   Vector Search in a workspace, same `search(query, k)` shape.
4. **Governance seam** (`pre_tool_hook`) — every tool call passes one
   callable before execution. That is where agent-control-plane's gate
   attaches (see `examples/gated_agent.py`).

## Why a plain-Python reference loop

Frameworks (LangGraph included) hide the loop. The loop is where cost,
loops-without-progress, and un-governed tool calls actually happen, so the
kit teaches it explicitly, then shows the same trio (registry, executor,
model) wrapped in a LangGraph graph for teams standardising on it.
