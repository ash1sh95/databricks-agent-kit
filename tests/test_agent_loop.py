import pytest

from agent_kit import Agent, MockModel
from examples.workspace_insight_agent import build_agent, build_registry


def test_agent_uses_billing_tool_and_answers_with_total():
    result = build_agent().run("What is our total billing cost and spend?")
    assert result.tools_used == ["query_billing"]
    assert "$1,424.95" in result.answer
    kinds = [e.kind for e in result.trace]
    assert kinds[0] == "question" and "tool_call" in kinds and kinds[-1] == "final"


def test_agent_failed_jobs():
    result = build_agent().run("Which jobs failed?")
    assert result.tools_used == ["query_failed_jobs"]
    assert "feature-refresh" in result.answer


def test_agent_docs_question_uses_rag_tool():
    result = build_agent().run("What does the documentation say about retention policy?")
    assert result.tools_used == ["search_docs"]
    assert "90 days" in result.answer


def test_agent_unknown_question_answers_without_tools():
    result = build_agent().run("What is the weather today?")
    assert result.tools_used == []
    assert "billing" in result.answer


def test_pre_tool_hook_can_block_calls():
    def deny_all(name, args):
        raise PermissionError(f"blocked: {name}")

    agent = Agent(build_registry(), model=MockModel(), pre_tool_hook=deny_all)
    with pytest.raises(PermissionError):
        agent.run("What is our total billing cost?")


def test_langgraph_path_is_optional():
    from agent_kit import build_langgraph_agent

    try:
        import langgraph  # noqa: F401

        assert build_langgraph_agent(build_agent()) is not None
    except ImportError:
        assert build_langgraph_agent(build_agent()) is None
