FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY examples ./examples
COPY evals ./evals
RUN pip install --no-cache-dir -e .
ENV PYTHONPATH=/app/src:/app
CMD ["python", "examples/workspace_insight_agent.py"]
