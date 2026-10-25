"""Configuration for agent-kit.

Two sources, in increasing precedence:
  1. A config file — JSON, or a small YAML-lite subset (see ``parse_yaml_lite``)
     so the same file shape can sit next to a ``databricks.yml`` bundle config.
  2. Environment variables (``AGENT_KIT_*``) — the only place secrets may live.
     The kit never reads secrets from files.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


def get_secret(name: str, default: str | None = None) -> str | None:
    """Read a secret from the environment only.

    On Databricks, inject secrets as environment variables from a secret
    scope (or use OAuth / workload identity) — never hard-code them in a
    notebook or commit them to a repo.
    """
    return os.environ.get(name, default)


def _coerce(raw: str):
    raw = raw.strip()
    if raw.lower() in {"true", "false"}:
        return raw.lower() == "true"
    for conv in (int, float):
        try:
            return conv(raw)
        except ValueError:
            pass
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]
    return raw


def parse_yaml_lite(text: str) -> dict:
    """Parse a deliberately small YAML subset: nested string-keyed maps with
    scalar values, two-space indentation, ``#`` comments. No lists, no anchors.

    This exists so the kit needs no PyYAML dependency for the simple config
    files it ships. Anything richer belongs in JSON or a real YAML parser.
    """
    root: dict = {}
    stack: list[tuple[int, dict]] = [(-1, root)]
    for line in text.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, sep, value = line.strip().partition(":")
        if not sep:
            raise ValueError(f"YAML-lite: expected 'key: value', got: {line!r}")
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value.strip() == "":
            child: dict = {}
            parent[key.strip()] = child
            stack.append((indent, child))
        else:
            parent[key.strip()] = _coerce(value)
    return root


@dataclass
class AgentKitConfig:
    model_endpoint: str = "mock"
    catalog: str = "main"
    schema: str = "agent_kit"
    experiment: str = "/Shared/agent-kit-evals"
    max_steps: int = 6
    temperature: float = 0.0
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: dict) -> AgentKitConfig:
        known = {f for f in cls.__dataclass_fields__} - {"extra"}
        cfg = cls(**{k: v for k, v in data.items() if k in known})
        cfg.extra = {k: v for k, v in data.items() if k not in known}
        return cfg

    def apply_env(self) -> AgentKitConfig:
        mapping = {
            "AGENT_KIT_MODEL_ENDPOINT": "model_endpoint",
            "AGENT_KIT_CATALOG": "catalog",
            "AGENT_KIT_SCHEMA": "schema",
            "AGENT_KIT_EXPERIMENT": "experiment",
        }
        for env, attr in mapping.items():
            if os.environ.get(env):
                setattr(self, attr, os.environ[env])
        if os.environ.get("AGENT_KIT_MAX_STEPS"):
            self.max_steps = int(os.environ["AGENT_KIT_MAX_STEPS"])
        return self


def load_config(path: str | Path | None = None) -> AgentKitConfig:
    """Load config from a .json or YAML-lite file (auto-detected by suffix),
    then apply environment overrides."""
    if path is None:
        return AgentKitConfig().apply_env()
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    data = json.loads(text) if p.suffix == ".json" else parse_yaml_lite(text)
    # Allow either a flat mapping or one nested under an "agent_kit:" key,
    # mirroring how bundle variables group settings in databricks.yml.
    if isinstance(data.get("agent_kit"), dict):
        data = data["agent_kit"]
    return AgentKitConfig.from_mapping(data).apply_env()
