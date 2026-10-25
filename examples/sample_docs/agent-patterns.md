# Agent patterns for this workspace

Agents should call tools through Unity Catalog functions so permissions
are governed centrally. Every agent run should be traced in MLflow and
evaluated against a versioned dataset before promotion. Human approval is
required before an agent takes a destructive or external-facing action,
and every tool decision should be auditable after the fact.
