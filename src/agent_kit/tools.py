"""Tool registry: define a tool once, run it locally or on Databricks.

A tool is declared as a Unity Catalog-style function spec — a name, a plain
language description, and typed parameters — because that is exactly how a
UC function is declared in Unity Catalog, and because an LLM picks tools
from descriptions, not from Python signatures.

The same spec then runs three ways:
  * ``LocalExecutor``     — in-process Python handler (dev, tests, CI).
  * ``DatabricksUCExecutor`` — interface stub for calling the UC function
    through a SQL warehouse / Statements API in a real workspace.
  * A governance gate (see agent-control-plane) can wrap either executor
    without the agent code changing — executors are the seam.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# Python type -> Unity Catalog / SQL type used in generated DDL.
_SQL_TYPES = {str: "STRING", int: "BIGINT", float: "DOUBLE", bool: "BOOLEAN"}


@dataclass
class Parameter:
    name: str
    type: type = str
    description: str = ""
    required: bool = True
    default: Any = None

    def json_schema(self) -> dict:
        py_to_json = {str: "string", int: "integer", float: "number", bool: "boolean"}
        return {"type": py_to_json.get(self.type, "string"), "description": self.description}


@dataclass
class ToolSpec:
    """A Unity Catalog-style function specification for one tool."""

    name: str
    description: str
    parameters: list[Parameter] = field(default_factory=list)
    returns: str = "STRING"
    comment: str = ""

    def json_schema(self) -> dict:
        """OpenAI/Model-Serving-style function schema, derived from the spec."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {p.name: p.json_schema() for p in self.parameters},
                "required": [p.name for p in self.parameters if p.required],
            },
        }

    def to_uc_ddl(self, catalog: str, schema: str) -> str:
        """Render a CREATE FUNCTION stub for registering this spec in UC.

        The body is a placeholder: in a workspace the function body would be
        SQL or a Python UDF. Emitting the DDL from the same spec that drives
        local execution keeps the two from drifting apart.
        """
        params = ", ".join(
            f"{p.name} {_SQL_TYPES.get(p.type, 'STRING')}" for p in self.parameters
        )
        comment = (self.comment or self.description).replace("'", "''")
        return (
            f"CREATE OR REPLACE FUNCTION {catalog}.{schema}.{self.name}({params})\n"
            f"RETURNS {self.returns}\n"
            f"COMMENT '{comment}'\n"
            f"RETURN '<implement in SQL or as a Python UDF in your workspace>';"
        )


class ToolRegistry:
    """Specs + local handlers, keyed by tool name."""

    def __init__(self) -> None:
        self._specs: dict[str, ToolSpec] = {}
        self._handlers: dict[str, Callable[..., Any]] = {}

    def register(self, spec: ToolSpec, handler: Callable[..., Any]) -> ToolSpec:
        if spec.name in self._specs:
            raise ValueError(f"tool already registered: {spec.name}")
        self._specs[spec.name] = spec
        self._handlers[spec.name] = handler
        return spec

    def tool(self, name: str, description: str, parameters: list[Parameter] | None = None,
             returns: str = "STRING"):
        """Decorator form of register()."""

        def wrap(fn: Callable[..., Any]) -> Callable[..., Any]:
            self.register(ToolSpec(name, description, parameters or [], returns), fn)
            return fn

        return wrap

    def spec(self, name: str) -> ToolSpec:
        if name not in self._specs:
            raise KeyError(f"unknown tool: {name}. Known: {sorted(self._specs)}")
        return self._specs[name]

    def handler(self, name: str) -> Callable[..., Any]:
        self.spec(name)
        return self._handlers[name]

    def names(self) -> list[str]:
        return sorted(self._specs)

    def schemas(self) -> list[dict]:
        return [self._specs[n].json_schema() for n in self.names()]


class LocalExecutor:
    """Execute registered handlers in-process, with argument validation."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def execute(self, name: str, args: dict | None = None) -> Any:
        args = dict(args or {})
        spec = self.registry.spec(name)  # raises KeyError for unknown tools
        for p in spec.parameters:
            if p.required and p.name not in args:
                raise ValueError(f"tool {name}: missing required argument '{p.name}'")
            if p.name not in args and p.default is not None:
                args[p.name] = p.default
        unknown = set(args) - {p.name for p in spec.parameters}
        if unknown:
            raise ValueError(f"tool {name}: unexpected arguments {sorted(unknown)}")
        return self.registry.handler(name)(**args)


class DatabricksUCExecutor:
    """Interface stub: execute a Unity Catalog function in a workspace.

    A real implementation submits ``SELECT catalog.schema.tool(args...)``
    through the Databricks SQL Statements API (or a SQL warehouse via the
    Databricks SDK, the optional ``databricks`` extra) using workspace
    credentials — never a token committed to code. This stub exists so agent
    code is written against the interface from day one and unit-tested with
    ``LocalExecutor`` instead.
    """

    def __init__(self, catalog: str, schema: str, warehouse_id: str | None = None) -> None:
        self.catalog = catalog
        self.schema = schema
        self.warehouse_id = warehouse_id

    def build_sql(self, name: str, args: dict | None = None) -> str:
        args = args or {}
        rendered = ", ".join(f"'{str(v).replace(chr(39), chr(39) * 2)}'" for v in args.values())
        return f"SELECT {self.catalog}.{self.schema}.{name}({rendered})"

    def execute(self, name: str, args: dict | None = None) -> Any:
        try:
            import databricks.sdk  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "DatabricksUCExecutor needs the Databricks SDK and a workspace: "
                "pip install -e '.[databricks]', set DATABRICKS_HOST and use "
                "OAuth or a secret scope. Use LocalExecutor for offline work. "
                f"SQL it would run: {self.build_sql(name, args)}"
            ) from exc
        raise NotImplementedError(
            "Wire WorkspaceClient().statement_execution here in your workspace; "
            f"SQL it would run: {self.build_sql(name, args)}"
        )
