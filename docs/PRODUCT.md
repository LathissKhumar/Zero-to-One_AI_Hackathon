# CanonPulse Product Status

CanonPulse protects continuity across long serialized-fiction series through a cited narrative ledger, pre-publish checks, repair attribution, handoff, debt board, localization, cohort simulation, and discovery.

The current implementation scope is authoritative in [`canonpulse-16h-plan.md`](../canonpulse-16h-plan.md). Predictions and cohort reactions are synthetic demonstrations, not observed reader behavior.

## Local validation

```bash
uv sync
uv run --group dev pytest
uv run uvicorn app.main:app --port 8000
```

## Deployment validation

Use `scripts/smoke_golden_path.py` against the Databricks App after readiness succeeds. If governed inference exceeds the runbook latency threshold, use the precomputed golden path and disclose that zero live inference was used for the fallback.

Last validation is recorded in [`sessionhandoff.md`](../sessionhandoff.md).
