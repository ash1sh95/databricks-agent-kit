import pytest

from agent_kit import LocalExecutor, Parameter, ToolRegistry, ToolSpec


def make_registry():
    registry = ToolRegistry()
    registry.register(
        ToolSpec("add", "Add two numbers",
                 [Parameter("a", int, "first"), Parameter("b", int, "second", required=False, default=0)]),
        lambda a, b=0: a + b,
    )
    return registry


def test_register_and_execute():
    executor = LocalExecutor(make_registry())
    assert executor.execute("add", {"a": 2, "b": 3}) == 5
    assert executor.execute("add", {"a": 2}) == 2  # default applied


def test_decorator_registration_and_schema():
    registry = ToolRegistry()

    @registry.tool("echo", "Echo text back", [Parameter("text", str, "text to echo")])
    def echo(text):
        return text.upper()

    assert registry.names() == ["echo"]
    schema = registry.schemas()[0]
    assert schema["name"] == "echo"
    assert schema["parameters"]["required"] == ["text"]
    assert LocalExecutor(registry).execute("echo", {"text": "hi"}) == "HI"


def test_duplicate_registration_rejected():
    registry = make_registry()
    with pytest.raises(ValueError):
        registry.register(ToolSpec("add", "again"), lambda: None)


def test_unknown_tool_and_bad_args():
    executor = LocalExecutor(make_registry())
    with pytest.raises(KeyError):
        executor.execute("nope", {})
    with pytest.raises(ValueError):
        executor.execute("add", {})  # missing required 'a'
    with pytest.raises(ValueError):
        executor.execute("add", {"a": 1, "bogus": 2})


def test_uc_ddl_generated_from_spec():
    ddl = make_registry().spec("add").to_uc_ddl("main", "agent_kit")
    assert ddl.startswith("CREATE OR REPLACE FUNCTION main.agent_kit.add(")
    assert "a BIGINT" in ddl and "b BIGINT" in ddl
    assert "RETURNS STRING" in ddl


def test_databricks_executor_builds_sql_and_fails_clearly():
    from agent_kit import DatabricksUCExecutor

    executor = DatabricksUCExecutor("main", "agent_kit", warehouse_id="wh-1")
    assert executor.build_sql("add", {"a": 1}) == "SELECT main.agent_kit.add('1')"
    try:
        import databricks.sdk  # noqa: F401

        with pytest.raises(NotImplementedError):
            executor.execute("add", {"a": 1})
    except ImportError:
        with pytest.raises(RuntimeError, match="Databricks SDK"):
            executor.execute("add", {"a": 1})
