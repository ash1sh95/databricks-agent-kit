.PHONY: install test lint demo eval

install:
	pip install -e ".[dev]"

test:
	pytest -q

lint:
	ruff check src tests examples

demo:
	PYTHONPATH=src:. python examples/workspace_insight_agent.py

eval:
	PYTHONPATH=src:. python examples/run_evals.py
