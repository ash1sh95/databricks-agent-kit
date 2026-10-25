"""databricks-agent-kit: build production-grade agents on Databricks.

The kit is stdlib-first. Everything runs offline against a deterministic mock
model; Databricks, MLflow and LangGraph integrations sit behind optional
extras and clean interfaces.
"""
from .agent import Agent, AgentResult, build_langgraph_agent
from .config import AgentKitConfig, get_secret, load_config, parse_yaml_lite
from .evals import EvalCase, EvalReport, EvalRunner, load_dataset, score_case
from .model import MockModel, ModelClient, ModelResponse, ModelServingClient
from .rag import BM25Retriever, Chunk, Document, chunk_text
from .tools import (
    DatabricksUCExecutor,
    LocalExecutor,
    Parameter,
    ToolRegistry,
    ToolSpec,
)

__version__ = "0.1.0"

__all__ = [
    "Agent",
    "AgentKitConfig",
    "AgentResult",
    "BM25Retriever",
    "Chunk",
    "DatabricksUCExecutor",
    "Document",
    "EvalCase",
    "EvalReport",
    "EvalRunner",
    "LocalExecutor",
    "MockModel",
    "ModelClient",
    "ModelResponse",
    "ModelServingClient",
    "Parameter",
    "ToolRegistry",
    "ToolSpec",
    "build_langgraph_agent",
    "chunk_text",
    "get_secret",
    "load_config",
    "load_dataset",
    "parse_yaml_lite",
    "score_case",
]
