"""Model clients: one interface for a Model Serving endpoint and a mock.

Agent code depends on ``ModelClient`` only. In a workspace the client is
``ModelServingClient`` (a Foundation Model API / Model Serving endpoint
reached through AI Gateway). Everywhere else — CI, a laptop, this README —
it is ``MockModel``, which is deterministic: the same input always produces
the same tool call, so agent behaviour is unit-testable without an LLM.
"""
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ToolCall:
    name: str
    args: dict = field(default_factory=dict)


@dataclass
class ModelResponse:
    text: str = ""
    tool_call: ToolCall | None = None

    @property
    def is_final(self) -> bool:
        return self.tool_call is None


class ModelClient(Protocol):
    def complete(self, messages: list[dict], tools: list[dict]) -> ModelResponse:
        """messages: chat dicts; may include {'role': 'tool', 'name':..., 'content':...}."""
        ...


class MockModel:
    """Deterministic stand-in for an LLM, driven by intent rules.

    It is intentionally simple — keyword intent -> one tool -> summarise the
    tool result. Its job is to make the *system* (loop, tools, evals)
    testable, not to fake intelligence. Swap in a real endpoint and only
    this class changes.
    """

    # (keywords, tool, args-builder) evaluated in order against the question.
    # Documentation intent is checked first: a question *about the docs* that
    # happens to mention cost is a docs question, not a billing query.
    INTENTS = (
        (("retention", "policy", "documentation", "docs", "guideline"), "search_docs", {}),
        (("failed job", "failing job", "job fail", "pipeline fail", "failed", "failure"), "query_failed_jobs", {}),
        (("cost", "spend", "billing", "expensive", "charge"), "query_billing", {}),
    )

    def complete(self, messages: list[dict], tools: list[dict]) -> ModelResponse:
        tool_results = [m for m in messages if m.get("role") == "tool"]
        if tool_results:
            last = tool_results[-1]
            return ModelResponse(
                text=f"Based on {last['name']}: {last['content']}"
            )
        question = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"), ""
        ).lower()
        available = {t["name"] for t in tools}
        for keywords, tool, args in self.INTENTS:
            if tool in available and any(k in question for k in keywords):
                call_args = dict(args)
                if tool == "search_docs":
                    call_args = {"query": question}
                return ModelResponse(tool_call=ToolCall(tool, call_args))
        return ModelResponse(
            text="I can answer questions about workspace cost (billing), failed jobs, "
            "and the team's documentation. Try one of those."
        )


class ModelServingClient:
    """Minimal OpenAI-compatible client for a Databricks Model Serving /
    Foundation Model API endpoint (typically fronted by AI Gateway, which
    adds usage tracking, guardrails and rate limits in the workspace).

    Auth comes from the environment (DATABRICKS_TOKEN) or, in a workspace,
    from the SDK's unified auth — this class reads the token from env only
    and never logs it.
    """

    def __init__(self, endpoint: str, host: str | None = None, token: str | None = None) -> None:
        self.endpoint = endpoint
        self.host = (host or os.environ.get("DATABRICKS_HOST", "")).rstrip("/")
        self._token = token or os.environ.get("DATABRICKS_TOKEN", "")

    def complete(self, messages: list[dict], tools: list[dict]) -> ModelResponse:
        if not self.host or not self._token:
            raise RuntimeError(
                "ModelServingClient needs DATABRICKS_HOST and DATABRICKS_TOKEN "
                "(or run inside a workspace). Use MockModel for offline work."
            )
        payload = {"messages": messages, "tools": [
            {"type": "function", "function": t} for t in tools], "max_tokens": 512}
        req = urllib.request.Request(
            f"{self.host}/serving-endpoints/{self.endpoint}/invocations",
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {self._token}",
                     "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 (host from config)
            data = json.loads(resp.read())
        choice = (data.get("choices") or [{}])[0].get("message", {})
        calls = choice.get("tool_calls") or []
        if calls:
            fn = calls[0]["function"]
            return ModelResponse(tool_call=ToolCall(
                fn["name"], json.loads(fn.get("arguments") or "{}")))
        return ModelResponse(text=choice.get("content", ""))
