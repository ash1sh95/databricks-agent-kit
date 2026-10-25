# Cost optimisation notes

Prefer serverless and jobs compute over all-purpose clusters for scheduled
work. Enable cluster auto-termination after 20 minutes of inactivity.
Tag every job and cluster with an owner team so billing usage can be
attributed. Review foundation model API spend weekly; route high-volume,
low-complexity calls to smaller models and reserve large models for hard
reasoning.
