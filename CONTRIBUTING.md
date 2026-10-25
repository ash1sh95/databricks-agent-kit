# Contributing

PRs welcome — especially new eval cases and new tool patterns.

House rules:

1. **A failure becomes an eval case before it becomes a fix.** Add the
   case to `evals/dataset.jsonl` (or the relevant test), watch it fail,
   then fix.
2. **Core stays stdlib-only.** Databricks, MLflow and LangGraph code goes
   behind the optional extras and the existing interfaces
   (`ModelClient`, executors, retrievers), with a deterministic offline
   path that keeps CI green without a workspace.
3. **No secrets, ever.** Config from files, secrets from environment
   variables only. Sample data must be synthetic.
4. **Tests + lint before push:**

```bash
pip install -e ".[dev]"
pytest -q
ruff check src tests examples
PYTHONPATH=src:. python examples/run_evals.py
```
