# Databricks notebook source
# MAGIC %md
# MAGIC # agent-kit on Databricks — deploy & run the workspace-insight agent
# MAGIC
# MAGIC This notebook runs the kit inside a workspace in ~15 minutes:
# MAGIC 1. Installs the package from this repo (Git folder) / via `%pip`.
# MAGIC 2. Sets widgets for catalog, schema and MLflow experiment.
# MAGIC 3. Registers the example tools as Unity Catalog-style specs and prints
# MAGIC    the CREATE FUNCTION DDL you would run to persist them in UC.
# MAGIC 4. Runs the mini agent. If a Model Serving endpoint widget is set, it
# MAGIC    uses it; otherwise it falls back to the deterministic MockModel so
# MAGIC    the notebook always succeeds end-to-end.
# MAGIC 5. Runs the shipped eval dataset and logs results to MLflow
# MAGIC    (and to a Delta table if the `write_delta` widget is on).
# MAGIC
# MAGIC No tokens are hard-coded: in a workspace, auth comes from the
# MAGIC notebook's identity / secret scopes.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 0. Widgets

# COMMAND ----------

dbutils.widgets.text("catalog", "main", "Unity Catalog catalog")
dbutils.widgets.text("schema", "agent_kit", "Unity Catalog schema")
dbutils.widgets.text("experiment", "/Shared/agent-kit-evals", "MLflow experiment")
dbutils.widgets.text("model_endpoint", "", "Model Serving endpoint (blank = mock model)")
dbutils.widgets.dropdown("write_delta", "false", ["true", "false"], "Write eval results to Delta")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
experiment = dbutils.widgets.get("experiment")
endpoint = dbutils.widgets.get("model_endpoint")
write_delta = dbutils.widgets.get("write_delta") == "true"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Install the kit
# MAGIC Point `%pip install` at your Git folder checkout of this repo, or at a
# MAGIC wheel you built from it (`python -m build`). A local path is shown.

# COMMAND ----------

# %pip install /Workspace${path_to_repo_root}
# RESTART PYTHON AFTER INSTALL IN A REAL WORKSPACE.

import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), "src"))  # Git-folder layout fallback
sys.path.insert(0, os.getcwd())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Build the agent (UC-style tools, Model Serving or mock model)

# COMMAND ----------

from agent_kit import Agent, ModelServingClient, load_config  # noqa: E402
from examples.workspace_insight_agent import build_registry  # noqa: E402

cfg = load_config()
cfg.catalog, cfg.schema, cfg.experiment = catalog, schema, experiment

registry = build_registry()
for spec in registry._specs.values():
    print(spec.to_uc_ddl(catalog, schema))
    print("---")

model = None
if endpoint:
    # Host/token come from the workspace runtime — never literals here.
    model = ModelServingClient(endpoint=endpoint)
    print(f"Using Model Serving endpoint: {endpoint}")
else:
    print("No endpoint widget set — using the deterministic MockModel.")

agent = Agent(registry, model=model) if model else None

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Run the mini agent

# COMMAND ----------

if agent is None:
    from examples.workspace_insight_agent import build_agent

    agent = build_agent()

for question in [
    "What is our total billing cost and spend this month?",
    "Which jobs failed?",
    "What does the documentation say about data retention policy?",
]:
    result = agent.run(question)
    print("=" * 72)
    for event in result.trace:
        print(event)
    print("ANSWER:", result.answer)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Evaluate, log to MLflow (and Delta if enabled)

# COMMAND ----------

from agent_kit import EvalRunner, load_dataset  # noqa: E402
from examples.workspace_insight_agent import build_agent  # noqa: E402

cases = load_dataset("evals/dataset.jsonl")
report = EvalRunner(build_agent).run_and_log_mlflow(cases, experiment)
print(report.summary())

if write_delta:
    rows = [(r.case_id, r.passed, ",".join(r.tools_used), r.answer) for r in report.results]
    df = spark.createDataFrame(rows, "case_id STRING, passed BOOLEAN, tools STRING, answer STRING")
    df.write.mode("overwrite").saveAsTable(f"{catalog}.{schema}.agent_kit_eval_results")
    print(f"Wrote {len(rows)} rows to {catalog}.{schema}.agent_kit_eval_results")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next steps
# MAGIC - Govern this agent: wrap the executor with agent-control-plane's
# MAGIC   gate (see `examples/gated_agent.py` in this repo).
# MAGIC - Observe it: send MLflow traces to the dashboards in
# MAGIC   dspy-observability-dashboard.
# MAGIC - Promote it: package the eval job with the Asset Bundle in
# MAGIC   `databricks/databricks.yml` (see databricks/README.md).
