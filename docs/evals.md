# Eval guide

## Philosophy

Score what the agent **did** — which tool it chose, and whether the answer
contains the facts that tool exists to provide — not just whether the
answer *sounds* right. Tool choice is observable and debuggable; vibes are
not.

## Dataset format

One JSON object per line in `evals/dataset.jsonl`:

```json
{"id": "billing-total", "question": "What is our total billing cost and spend this month?", "expected_tool": "query_billing", "expected_contains": ["$", "total spend"]}
```

- `expected_tool` — the tool a correct agent must use (or `null` when the
  right behaviour is to answer without tools).
- `expected_contains` — substrings the answer must contain
  (case-insensitive). Prefer facts from tool output ("$1,424.95"-style
  totals, a job name, "90 days") over phrasing — facts survive model swaps.

## Running

```bash
PYTHONPATH=src:. python examples/run_evals.py     # local scorer, exits 1 on any failure
```

In a workspace, `EvalRunner.run_and_log_mlflow(cases, experiment)` logs
pass-rate and per-case metrics to an MLflow experiment (the notebook in
`databricks/` does this). Richer judge-based scoring belongs in
Databricks' agent evaluation tooling on top of the same dataset.

## Growing the dataset

1. Every production failure becomes a case **before** it becomes a fix.
2. Include at least one `expected_tool: null` case — agents that call tools
   when they shouldn't are a real failure class.
3. Keep the mock-model suite at 100%: the mock is deterministic, so a
   failure there is a system regression, never flakiness.
4. Re-run after every model endpoint change: the dataset is your contract
   with the new model.

## Reading results

The summary prints per-case tools used and pass/fail with reasons
("expected tool X, used Y", "answer missing '…'"). Start from the reason,
not the score — the score only tells you something changed.
