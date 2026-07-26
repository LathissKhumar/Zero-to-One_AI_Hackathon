# CanonPulse Databricks Operations Specification

## Purpose

Make Databricks a working substrate for governed ingestion, extraction,
retrieval, model evaluation, and application serving. Configuration assets are
not considered complete until a workspace run proves the path.

## Resources

Unity Catalog owns series, episodes, extraction runs, nodes, edges, excerpts,
ledger entries, resolved snapshots, boundary features, predictions, variants,
cohorts, reactions, manifests, and evaluation runs. Tables are versioned by
series and source/extraction version where applicable.

The bundle parameterizes catalog, schema, warehouse, model endpoint, Vector
Search index, App configuration, and MLflow experiment. No token, workspace
URL containing credentials, or unreviewed generated data is committed.

## Governed flows

1. Load a series and manifest idempotently.
2. Run synopsis extraction and record a job.
3. Run deep extraction as one batched `ai_query` over Delta rows.
4. Validate and promote graph output atomically.
5. Materialize ledger snapshots and boundary features.
6. Run training/evaluation and log the MLflow artifact.
7. Run blind cohort reactions as one governed cross join.
8. Serve read APIs from Delta and model APIs from configured Databricks
   endpoints.

Each flow writes run ID, input version, model version, row counts, failures,
latency, and cost metadata. Failed runs do not replace the last good version.

## Deployment modes

- `demo`: local committed data, no credentials, no live inference.
- `workspace`: Databricks App plus configured SQL warehouse, model endpoint,
  Vector Search, and MLflow experiment.
- `offline_bundle`: precomputed read-only results for unreliable network
  conditions; every response declares degraded/offline state.

Configuration absence in workspace mode is a visible startup or request error,
not a silent switch to demo data.

## Acceptance criteria

- `databricks bundle validate` succeeds with supplied variables.
- DDL, loader, extraction, feature, cohort, and evaluation jobs run against a
  test schema.
- Unity Catalog lineage connects findings to source excerpts and extraction
  runs.
- The deployed App reads workspace data and does not import the fixed demo
  singleton.
- Model-serving calls are governed and carry model/version metadata.
- A failed live call switches only to a declared offline bundle when configured
  to do so.

## Tests and operational checks

Static tests validate placeholders, no secrets, `ai_query` use, schema
coupling, and bundle resources. A workspace smoke test validates auth, DDL,
row loading, one extraction batch, one feature snapshot, one MLflow run, one
cohort query, Vector Search lookup, and App health. The smoke test is gated on
explicit credentials and is never part of offline pytest.
