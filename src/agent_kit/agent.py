"""The agent loop: model proposes, tools execute, model answers.

The reference implementation is a plain Python loop because the loop is the
part people need to *read* when learning agent systems — frameworks hide it.
An optional LangGraph path (``build_langgraph_agent``) wraps the same
registry/executor/model trio for teams standardising on LangGraph, which
Databricks' Mosaic AI Agent Framework also supports for deployment.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .model import MockModel, ModelClient
from .tools import LocalExecutor, ToolRegistry


@dataclass
class TraceEvent:
    kind: str  # "question" | "tool_call" | "tool_result" | "final"
    detail: str

    def __str__(self) -> str:
        return f"[{self.kind}] {self.detail}"


@dataclass
class AgentResult:
    answer: str
    trace: list[TraceEvent] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)


class Agent:
    """A bounded tool-using loop over injected registry/executor/model.

    ``pre_tool_hook`` is the governance seam: pass a callable
    ``hook(name, args) -> None`` (raise to block) to gate every call — the
    examples show it wired to agent-control-plane's gate concepts.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        model: ModelClient | None = None,
        executor: Any | None = None,
        max_steps: int = 6,
        pre_tool_hook: Callable[[str, dict], None] | None = None,
    ) -> None:
        self.registry = registry
        self.model = model or MockModel()
        self.executor = executor or LocalExecutor(registry)
        self.max_steps = max_steps
        self.pre_tool_hook = pre_tool_hook

    def run(self, question: str) -> AgentResult:
        trace = [TraceEvent("question", question)]
        tools_used: list[str] = []
        messages: list[dict] = [
            {"role": "system", "content": "You answer questions using the available tools."},
            {"role": "user", "content": question},
        ]
        for _ in range(self.max_steps):
            response = self.model.complete(messages, self.registry.schemas())
            if response.is_final:
                trace.append(TraceEvent("final", response.text))
                return AgentResult(answer=response.text, trace=trace, tools_used=tools_used)
            call = response.tool_call
            assert call is not None
            trace.append(TraceEvent("tool_call", f"{call.name}({call.args})"))
            if self.pre_tool_hook is not None:
                self.pre_tool_hook(call.name, call.args)
            result = self.executor.execute(call.name, call.args)
            tools_used.append(call.name)
            trace.append(TraceEvent("tool_result", f"{call.name} -> {result}"))
            messages.append({"role": "assistant", "content": "", "tool_call": call.name})
            messages.append({"role": "tool", "name": call.name, "content": str(result)})
        raise RuntimeError(f"agent exceeded max_steps={self.max_steps} without a final answer")


def build_langgraph_agent(agent: Agent):
    """Return a LangGraph StateGraph equivalent of ``agent``, or None.

    LangGraph is an optional extra (``pip install -e '.[langgraph]'``). The
    graph has the same two nodes the reference loop has — call_model and
    call_tool — so behaviour (and the governance hook) carries over.
    Returns None when langgraph is not installed; callers fall back to
    ``Agent.run``.
    """
    try:
        from langgraph.graph import END, StateGraph  # type: ignore
    except ImportError:
        return None

    def call_model(state: dict) -> dict:
        resp = agent.model.complete(state["messages"], agent.registry.schemas())
        return {"response": resp, "messages": state["messages"]}

    def call_tool(state: dict) -> dict:
        call = state["response"].tool_call
        if agent.pre_tool_hook is not None:
            agent.pre_tool_hook(call.name, call.args)
        result = agent.executor.execute(call.name, call.args)
        state["messages"].append({"role": "tool", "name": call.name, "content": str(result)})
        return {"messages": state["messages"]}

    graph = StateGraph(dict)
    graph.add_node("model", call_model)
    graph.add_node("tool", call_tool)
    graph.set_entry_point("model")
    graph.add_conditional_edges(
        "model", lambda s: "tool" if not s["response"].is_final else END,
        {"tool": "tool", END: END},
    )
    graph.add_edge("tool", "model")
    return graph.compile()


def demo_main() -> None:  # pragma: no cover - console entry point
    print("Run the full demo: PYTHONPATH=src:. python examples/workspace_insight_agent.py")
