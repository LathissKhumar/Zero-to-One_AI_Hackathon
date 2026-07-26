# CanonPulse Demo Runbook

## Prerequisites

Use Python 3.11–3.14 and `uv`. Keep demo and cohort metrics labeled synthetic. Never place tokens, `.env` files, or generated `mlruns/` data in the repository.

## Local offline demo

```bash
uv sync
uv run --group dev pytest
uv run uvicorn app.main:app --port 8000
```

Open `http://127.0.0.1:8000`. The local path uses committed synthetic series data and deterministic adapters.

## Governed Databricks demo

1. Apply `sql/ddl.sql` to the configured Unity Catalog schema.
2. For user documents, put supported files in a Unity Catalog Volume and run:

```bash
uv run python scripts/run_document_processing.py \
  --warehouse <warehouse-id> \
  --source-path /Volumes/<catalog>/<volume-schema>/<folder>/ \
  --series-id <series-id>
```

   This uses Databricks `ai_parse_document` and writes the raw and parsed
   document layers. Normalize its `document.elements` output with
   `app/document_ingestion.py`; do not skip the episode-boundary review gate.
3. Alternatively, load the deterministic demo series with `uv run python scripts/load_databricks.py --warehouse <warehouse-id>`.
4. Sync retrieval with `uv run python scripts/build_vector_index.py --warehouse <warehouse-id> --index-name <index> --endpoint-name <endpoint>`.
5. Run the deployed app’s health endpoint and then run:

```bash
uv run python scripts/smoke_golden_path.py \
  --base-url "$CANONPULSE_BASE_URL" \
  --series-id last-monsoon \
  --version-id demo \
  --max-latency-ms 5000
```

## Fallback gate

If a governed call exceeds the latency threshold or readiness is unavailable, switch to the precomputed golden path. The fallback uses cached Delta reads and zero live inference; disclose this in the rehearsal record.

## Rehearsal checklist

Run the smoke command six times. Record only commit SHA, deployment ID, model/schema versions, endpoint status, and timings. Do not record headers, tokens, source text, or credential-bearing URLs. A rehearsal is complete only when all six runs pass with citations and model linkage.
