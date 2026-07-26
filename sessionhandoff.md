# CanonPulse Session Handoff

## Current status

The implementation uses synthetic demo and training data. Predictions and cohort reactions are not measured reader behavior. The authoritative scope is [`canonpulse-16h-plan.md`](canonpulse-16h-plan.md).

## Last validation

```text
uv run --group dev pytest
```

The latest local validation passed after the eight gap work began; the suite count is recorded in the final execution report. Deployment rehearsal evidence must be generated with `scripts/smoke_golden_path.py` and must not contain credentials or raw tokens.

## Gap execution plans

| Gap | Plan | Status |
|---|---|---|
| 1 | [gap-01 ingestion](docs/superpowers/plans/2026-07-26-canonpulse-gap-01-ingestion-lifecycle.md) | implemented locally |
| 2 | [gap-02 provenance](docs/superpowers/plans/2026-07-26-canonpulse-gap-02-extraction-provenance.md) | implemented locally |
| 3 | [gap-03 feature contract](docs/superpowers/plans/2026-07-26-canonpulse-gap-03-feature-contract-and-model.md) | implemented locally |
| 4 | [gap-04 graph agents](docs/superpowers/plans/2026-07-26-canonpulse-gap-04-graph-agents-and-variants.md) | implemented locally |
| 5 | [gap-05 retrieval](docs/superpowers/plans/2026-07-26-canonpulse-gap-05-cohorts-and-retrieval.md) | implemented locally |
| 6 | [gap-06 API/UI](docs/superpowers/plans/2026-07-26-canonpulse-gap-06-api-and-ui-completeness.md) | implemented locally |
| 7 | [gap-07 operations](docs/superpowers/plans/2026-07-26-canonpulse-gap-07-operations-and-observability.md) | implemented locally |
| 8 | [gap-08 closure](docs/superpowers/plans/2026-07-26-canonpulse-gap-08-documentation-and-demo-closure.md) | documentation in progress |
