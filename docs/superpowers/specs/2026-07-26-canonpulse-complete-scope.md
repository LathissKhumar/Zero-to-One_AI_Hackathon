# CanonPulse Complete Scope Specification

**Status:** Proposed implementation baseline.

**Authority:** `canonpulse-16h-plan.md` is the product scope. This document
maps every surface and architecture item in that plan to a focused
specification and implementation plan. Existing 2026-07-25 documents remain
historical design records; this document resolves their deliberately deferred
items.

## Product outcome

A writer submits a complete serialized series or a new episode. CanonPulse
builds a cited, versioned narrative ledger; distinguishes real holes from
intentional twists; ranks narrative debt; predicts next-episode continuation
from graph features; evaluates repairs through the same frozen model; and
exposes memory, handoff, portfolio, localization, cohort, and discovery
surfaces over the same ledger.

The product remains platform-independent. Pocket FM is a reference customer,
not a runtime dependency. Demo series, cohort reactions, and training labels
remain synthetic until a separately governed real-data program exists.

## Coverage matrix

| Canonical plan item | Specification | Implementation plan |
|---|---|---|
| Domain language and invariants | `01-domain-and-graph.md` | CP-001, CP-002, CP-003 |
| Series ingest and two-speed processing | `02-ingestion-and-extraction.md` | CP-004, CP-005 |
| Dual-layer graph and ledger | `01-domain-and-graph.md` | CP-001, CP-003 |
| Backward payoff verification | `01-domain-and-graph.md` | CP-003 |
| Real training-corpus fusion | `03-training-and-prediction.md` | CP-006, CP-007 |
| Feature vector and continuation model | `03-training-and-prediction.md` | CP-008, CP-009 |
| MLflow evaluation and lineage | `03-training-and-prediction.md` | CP-010, CP-019 |
| Surgical node repair | `04-repair-and-graph-agents.md` | CP-011 |
| Non-linear scrambler | `04-repair-and-graph-agents.md` | CP-012 |
| Micro-foreshadowing | `04-repair-and-graph-agents.md` | CP-013 |
| Five Writers Room personas | `04-repair-and-graph-agents.md` | CP-014 |
| Series Memory | `05-product-surfaces.md` | CP-015 |
| Pre-Publish Check | `05-product-surfaces.md` | CP-016 |
| Writer Handoff Sheet | `05-product-surfaces.md` | CP-017 |
| Showrunner Debt Board | `05-product-surfaces.md` | CP-018 |
| Localization Continuity Check | `05-product-surfaces.md` | CP-019 |
| Five listener cohorts and blind evaluation | `06-cohorts-discovery-retrieval.md` | CP-020 |
| Vector Search and discovery | `06-cohorts-discovery-retrieval.md` | CP-021 |
| Delta, Unity Catalog, `ai_query`, App, serving | `07-databricks-operations.md` | CP-022, CP-023 |
| API and frontend surfaces | `08-api-ui-demo.md` | CP-024, CP-025 |
| Offline fallback, security, observability | `09-quality-security-and-demo.md` | CP-026, CP-027 |
| Full test and rehearsal gates | `09-quality-security-and-demo.md` | CP-028 |

## Completion rule

No row in the coverage matrix is considered complete until its specification's
acceptance criteria and its plan task's tests pass. A SQL file, Pydantic model,
or deployment variable by itself is a scaffold, not a shipped feature.

## Cross-cutting seams

The implementation uses these deep module seams:

- `SeriesRepository`: versioned series and episode persistence.
- `ExtractionAdapter`: synopsis, local model, and Databricks `ai_query`
  implementations behind one extraction interface.
- `GraphBuilder`: extraction result to validated dual-layer graph.
- `LedgerResolver`: graph plus verifier to cited ledger states.
- `FeatureProjector`: boundary ledger to structural feature vector.
- `ContinuationModel`: train, predict, counterfactual score, and report model
  metadata.
- `VariantEngine`: immutable original plus repair/scrambler variants.
- `EvidenceRepository`: citation and semantic retrieval.
- `SurfaceQuery`: product-specific read models over the ledger.

HTTP handlers, SQL jobs, and frontend code consume these seams rather than
reimplementing domain rules.

## Non-goals

CanonPulse will not claim real audience calibration without licensed labels;
generate a full replacement episode; publish to a platform; clone voices;
make legal or editorial decisions for a showrunner; or silently substitute
synthetic data for missing production data.
