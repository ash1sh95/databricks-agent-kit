# Data retention guideline

Raw landing tables are retained for 90 days. Curated Delta tables in the
silver and gold layers are retained for 400 days to cover year-over-year
reporting. MLflow experiment artifacts follow the experiment retention of
400 days unless a model is registered, in which case model versions are
kept until explicitly deprecated by the owning team.

Temporary agent scratch tables must be dropped within 7 days. Owners are
responsible for lifecycle rules on tables they create.
