# Gap 7 — Operations, Health, and Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide production health checks, request-to-run-to-cost correlation, model/retrieval freshness checks, evaluation linkage, and a repeatable golden-path smoke test.

**Architecture:** Request middleware creates a request ID and trace context; ingestion, extraction, prediction, retrieval, and cohort runs emit structured events linked by `request_id`, `run_id`, `model_version`, and `source_version`. Health checks are separated into liveness and readiness, with dependency-specific results. A smoke script exercises the deployed app and exits nonzero on stale assets, missing citations, ungoverned inference, or latency violations.

**Tech Stack:** FastAPI middleware, MLflow, Delta/Databricks SQL, Databricks Apps, pytest, `uv`.

## Global Constraints

- Never commit tokens, `.env`, generated `mlruns/`, or secret-bearing workspace URLs.
- Local tests cannot require Databricks credentials or network access.
- Every runtime inference event identifies governed model endpoint, model version, and request/run IDs.
- Keep synthetic cohort and demo metrics explicitly labeled.
- Health checks must distinguish liveness from readiness and report actionable dependency names.

---

## File map

- Create `app/observability.py`: event schema, context, and emitters.
- Create `app/health.py`: liveness/readiness checks.
- Modify `app/main.py`: middleware and health endpoints.
- Modify `app/ingestion.py`, `app/extraction.py`, `app/predictor.py`, and `app/cohorts.py`: event linkage.
- Create `scripts/smoke_golden_path.py`: deployed rehearsal checker.
- Create `tests/test_observability.py` and `tests/test_health.py`; modify `tests/test_api_v2.py`.

## Task 1: Define correlated operational events

**Files:**
- Create: `app/observability.py`
- Test: `tests/test_observability.py`

**Interfaces:**
- Produces `RunContext(request_id, run_id, series_id, version_id, source_version, model_version)`.
- Produces `OperationalEvent(event_name, context, started_at, finished_at, latency_ms, status, cost_usd, metadata)`.
- Produces `EventSink.emit(event: OperationalEvent) -> None`.

- [ ] **Step 1: Write the failing test**

```python
def test_event_requires_run_and_request_correlation():
    with pytest.raises(ValueError, match="request_id"):
        OperationalEvent(event_name="prediction", context=RunContext(
            request_id="", run_id="r1", series_id="s", version_id="v",
            source_version="sv", model_version="m"), status="ok")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_observability.py -v`

Expected: FAIL because the event contract and sink do not exist.

- [ ] **Step 3: Write minimal implementation**

Define required IDs, monotonic latency calculation, non-negative cost validation, explicit statuses `ok|failed|rejected|timeout`, and an in-memory sink that preserves insertion order for tests.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_observability.py -v`

Expected: PASS for event validation, serialization, and sink ordering.

- [ ] **Step 5: Commit**

```bash
git add app/observability.py tests/test_observability.py
git commit -m "feat: define correlated operational events"
```

## Task 2: Instrument requests, model calls, retrieval, and evaluation linkage

**Files:**
- Modify: `app/main.py`, `app/ingestion.py`, `app/extraction.py`, `app/predictor.py`, `app/cohorts.py`
- Test: `tests/test_observability.py`, `tests/test_api_v2.py`

**Interfaces:**
- Middleware sets `request.state.run_context: RunContext`.
- Each service emits `OperationalEvent` with `event_name` in `request|ingestion|extraction|prediction|retrieval|cohort|evaluation`.
- MLflow tags are `request_id`, `run_id`, `series_id`, `version_id`, `source_version`, `model_version`, and `synthetic` where applicable.

- [ ] **Step 1: Write the failing test**

```python
def test_prediction_event_links_request_model_and_cost(fake_sink, client):
    response = client.get("/api/v2/series/s1/health", headers={"X-Series-Ids": "s1"})
    event = fake_sink.events[-1]
    assert event.context.request_id == response.json()["request_id"]
    assert event.context.model_version
    assert event.cost_usd >= 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_observability.py tests/test_api_v2.py -k linkage -v`

Expected: FAIL because request IDs and service events are not connected end to end.

- [ ] **Step 3: Write minimal implementation**

Create the context in middleware, pass it through service calls, emit success/failure events in `finally` blocks, and record MLflow tags/metrics through the existing optional logger without creating network work in local mode.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_observability.py tests/test_api_v2.py -v`

Expected: PASS with one request event, linked service events, latency, rejection status, and cost fields.

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/ingestion.py app/extraction.py app/predictor.py app/cohorts.py tests/test_observability.py tests/test_api_v2.py
git commit -m "feat: instrument linked runtime operations"
```

## Task 3: Add liveness, readiness, freshness, and evaluation checks

**Files:**
- Create: `app/health.py`
- Modify: `app/main.py`
- Test: `tests/test_health.py`

**Interfaces:**
- `check_liveness() -> HealthReport` never calls external dependencies.
- `check_readiness(dependencies: HealthDependencies) -> HealthReport` checks store, model, retrieval index, and feature-schema freshness.
- `GET /health/live` returns 200 when process is responsive.
- `GET /health/ready` returns 200 only when all required dependencies are ready; otherwise 503 with per-check results.

- [ ] **Step 1: Write the failing test**

```python
def test_readiness_returns_503_for_stale_model_and_missing_index(client):
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["checks"]["model"]["status"] == "stale"
    assert response.json()["checks"]["retrieval"]["status"] == "missing"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_health.py -v`

Expected: FAIL because health endpoints and dependency checks are absent or always report healthy.

- [ ] **Step 3: Write minimal implementation**

Implement liveness without dependencies; readiness checks current model schema/version, latest extraction timestamp, vector-index row count, Delta store access, and evaluation linkage; return stable statuses `ready|stale|missing|error`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_health.py -v`

Expected: PASS for healthy, stale, missing, dependency-error, and liveness cases.

- [ ] **Step 5: Commit**

```bash
git add app/health.py app/main.py tests/test_health.py
git commit -m "feat: add actionable health and freshness checks"
```

## Task 4: Create the golden-path operational smoke test

**Files:**
- Create: `scripts/smoke_golden_path.py`
- Test: `tests/test_observability.py`

**Interfaces:**
- Script accepts `--base-url`, `--series-id`, `--version-id`, `--max-latency-ms`, and `--require-ready`.
- Script exits `0` only when health, ingest/status, ledger evidence, prediction, attribution, retrieval, and observability linkage pass.

- [ ] **Step 1: Write the failing test**

```python
def test_smoke_result_fails_when_prediction_has_no_model_linkage():
    result = run_smoke_with_fixture(prediction_model_version=None)
    assert result.exit_code == 1
    assert "model_version" in result.failures
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_observability.py -k smoke -v`

Expected: FAIL because the smoke result contract and checks do not exist.

- [ ] **Step 3: Write minimal implementation**

Call the endpoints in order, collect request IDs, verify every response has citations and model/schema metadata, measure each latency, reject ungoverned endpoint names, and print a redacted JSON report suitable for the rehearsal record.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_observability.py -k smoke -v`

Expected: PASS for a complete fixture and nonzero exit for each missing dependency or linkage field.

- [ ] **Step 5: Commit**

```bash
git add scripts/smoke_golden_path.py tests/test_observability.py
git commit -m "feat: add golden path operational smoke test"
```

## Self-review

- Spec coverage: health, freshness, model/retrieval checks, request/run/cost linkage, MLflow tags, evaluation linkage, and rehearsal automation are covered by Tasks 1–4.
- Completeness scan: the plan contains no unfinished marker or vague implementation instruction.
- Type consistency: middleware creates `RunContext`, all `OperationalEvent`s consume it, and health/smoke outputs use stable status names.
- Verification: run `uv run --group dev pytest tests/test_observability.py tests/test_health.py tests/test_api_v2.py -v`.
