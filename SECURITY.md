# Security

- **Secrets**: the kit reads secrets from environment variables only
  (`agent_kit.get_secret`). Never commit tokens to this repo, a notebook,
  or a bundle file. On Databricks, use secret scopes or workload identity.
- **Sample data**: everything under `examples/` is synthetic. Do not
  replace it with exports from a real workspace in a public fork.
- **Tool safety**: this kit builds agents; it does not govern them. For
  policy gating, approvals and audit of tool calls, compose it with
  agent-control-plane (see `examples/gated_agent.py`) before pointing
  tools at anything destructive or external.
- Report vulnerabilities via a GitHub issue marked `security` (do not
  include secrets or real data in the report).
