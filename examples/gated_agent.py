"""The same workspace-insight agent, gated.

Project 1 of this suite, **agent-control-plane**, governs agents with a
judge-before-action gate. This example shows the composition: the kit's
Agent accepts a ``pre_tool_hook``; the gate lives there, and the agent code
does not change.

If ``agent_control_plane`` is installed (e.g. ``pip install`` from the
sibling repo), the example adapts its ControlPlaneGate into a hook.
Otherwise it uses the clearly-labelled local shim below, which implements
just enough of the same interface — allow-list + per-tool call budget —
to demonstrate the seam. The shim is NOT the control plane; it has no
policies, judges, approvals or audit log.
"""
from __future__ import annotations

from typing import Protocol

from agent_kit import Agent, MockModel
from examples.workspace_insight_agent import build_registry


class Gate(Protocol):
    def check(self, tool_name: str, args: dict) -> None:
        """Raise to block the call."""
        ...


class ShimGate:
    """Minimal stand-in used only when agent-control-plane is not installed."""

    def __init__(self, allowed: set[str], per_tool_budget: int = 2) -> None:
        self.allowed = allowed
        self.per_tool_budget = per_tool_budget
        self._counts: dict[str, int] = {}

    def check(self, tool_name: str, args: dict) -> None:
        if tool_name not in self.allowed:
            raise PermissionError(f"gate: tool not allow-listed: {tool_name}")
        self._counts[tool_name] = self._counts.get(tool_name, 0) + 1
        if self._counts[tool_name] > self.per_tool_budget:
            raise PermissionError(f"gate: call budget exceeded for {tool_name}")


def make_hook() -> tuple[Gate, str]:
    try:
        from agent_control_plane.gate import ControlPlaneGate  # type: ignore

        gate = ControlPlaneGate()

        class _RealGate:
            def check(self, tool_name: str, args: dict) -> None:
                from agent_control_plane.models import ToolCall  # type: ignore

                decision = gate.evaluate(ToolCall(tool_name=tool_name, args=args,
                                                  case_id="gated-example", session_id="demo"))
                if not decision.allowed:
                    raise PermissionError(f"control-plane: {decision.verdict} — {decision.reason}")

        return _RealGate(), "agent-control-plane ControlPlaneGate"
    except ImportError:
        return ShimGate(allowed={"query_billing", "query_failed_jobs", "search_docs"}), \
            "local shim (agent-control-plane not installed)"


def main() -> None:
    gate, label = make_hook()
    print(f"Gate in use: {label}\n")
    agent = Agent(build_registry(), model=MockModel(),
                  pre_tool_hook=lambda name, args: gate.check(name, args))
    for question in [
        "What is our total billing cost?",
        "Which jobs failed?",
        "What is the data retention policy in the documentation?",
    ]:
        result = agent.run(question)
        print(f"Q: {question}\nA: {result.answer}\n")


if __name__ == "__main__":
    main()
