# Deploy in 15 minutes

Everything here is workspace-agnostic: no hosts, tokens or personal paths
are committed. You bring a workspace; the kit brings the agent.

## Path A — notebook only (fastest)

1. Add this repo to your workspace as a **Git folder**
   (Workspace → Create → Git folder, paste the repo URL).
2. Open `databricks/01_agent_kit_on_databricks.py`.
3. Set the widgets: `catalog`, `schema`, `experiment`. Leave
   `model_endpoint` blank for the first run — the notebook falls back to
   the deterministic MockModel, so run #1 always succeeds.
4. Run all. You will see:
   - the `CREATE FUNCTION` DDL for the three example tools (run it in a
     SQL editor / Catalog Explorer if you want the specs persisted in
     Unity Catalog),
   - the agent answering billing / failed-jobs / documentation questions
     with a full trace,
   - the eval table, logged to your MLflow experiment.
5. Second run: set `model_endpoint` to a Foundation Model API or Model
   Serving endpoint name (e.g. one fronted by AI Gateway) and re-run —
   only the model client changes.

## Path B — Asset Bundle (repeatable deploys)

```bash
pip install databricks-cli   # or your platform's CLI distribution
databricks bundle validate   # from this databricks/ folder
databricks bundle deploy -t dev
databricks bundle run -t dev agent_kit_eval_job
```

The bundle (`databricks.yml`) defines one serverless-style job that runs
the notebook as an eval job and writes results to
`<catalog>.<schema>.agent_kit_eval_results` when `write_delta` is on.
Add a `prod` deploy to your CI once dev is green. An `apps` block skeleton
is included (commented) for exposing the agent as a Databricks App.

## Going further

| Step | Where |
|---|---|
| Persist tools as real UC functions | The DDL printed by the notebook; bodies in SQL or Python UDFs |
| Govern tool calls | Wrap the executor with agent-control-plane (see `examples/gated_agent.py`) |
| Real retrieval | Replace BM25 with a Vector Search Delta Sync index (`agent_kit.rag.DatabricksVectorSearchRetriever`) |
| Trace & cost dashboards | MLflow tracing from the eval job + dspy-observability-dashboard patterns |
| Secrets | Secret scopes / environment injection only — the kit reads secrets from env, never from files |

## Troubleshooting

- **`ModuleNotFoundError: agent_kit`** — install from the Git folder
  (`%pip install /Workspace<path-to-repo>`) and restart Python, or run the
  notebook from the repo root so its `sys.path` fallback applies.
- **Model Serving call fails** — check the endpoint name in the widget and
  that the notebook's identity can invoke it; the mock fallback proves the
  rest of the pipeline independently.
- **Delta write fails** — the notebook identity needs CREATE/USE on the
  target catalog/schema; set `write_delta=false` to skip while debugging.
