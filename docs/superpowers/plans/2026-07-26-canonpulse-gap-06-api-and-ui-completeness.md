# Gap 6 — Authorized API and UI Completeness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace demo-singleton API behavior with authenticated series/version context and expose complete loading, error, evidence, comparison, approval, and cohort workflows in the browser.

**Architecture:** Resolve an `ActorContext` once per request, authorize series/version access before reading the store, and pass that context into every service. API responses use stable envelopes with request IDs. The frontend keeps server state per series/version, renders explicit loading/error/empty states, and makes approval actions auditable rather than mutating a global singleton.

**Tech Stack:** FastAPI, Pydantic, JavaScript/CSS static frontend, pytest/FastAPI `TestClient`.

## Global Constraints

- Preserve platform-independent vocabulary and synthetic-data disclosures.
- Every read and write must be scoped to an authorized `series_id` and `version_id`.
- Tests use fake actor contexts and in-memory stores; no real identity provider or network calls.
- API schemas and feature-vector ordering remain explicit and tested.
- Approval actions must be reversible or recorded with actor, timestamp, and request ID.

---

## File map

- Create `app/auth_context.py`: actor, authorization, and request-ID dependencies.
- Modify `app/main.py`: scope existing routes and add complete workflow routes.
- Modify `app/store.py`: series/version-aware reads and approval audit records.
- Modify `app/static/app.js`, `app/static/index.html`, and `app/static/styles.css`: stateful panels and workflow controls.
- Modify `tests/test_api_v2.py`, `tests/test_store.py`; create `tests/test_auth_context.py` and `tests/test_ui_contract.py`.

## Task 1: Add actor context and series/version authorization

**Files:**
- Create: `app/auth_context.py`
- Modify: `app/main.py`, `app/store.py`
- Test: `tests/test_auth_context.py`, `tests/test_api_v2.py`

**Interfaces:**
- Produces `ActorContext(actor_id: str, roles: frozenset[str], series_ids: frozenset[str])`.
- Produces `authorize_series(actor: ActorContext, series_id: str, version_id: str) -> None`.
- FastAPI dependency `get_actor_context(request: Request) -> ActorContext` reads testable headers `X-Actor-Id`, `X-Series-Ids`, and `X-Roles`.

- [ ] **Step 1: Write the failing test**

```python
def test_series_route_rejects_actor_without_series_access(client):
    response = client.get("/api/v2/series/secret/version/v1", headers={"X-Actor-Id": "writer-1"})
    assert response.status_code == 403

def test_series_route_does_not_read_demo_singleton(client):
    response = client.get("/api/v2/series/s1/version/v1", headers={"X-Series-Ids": "s1"})
    assert response.json()["series_id"] == "s1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_auth_context.py tests/test_api_v2.py -k authorization -v`

Expected: FAIL because routes currently use the demo series without actor authorization.

- [ ] **Step 3: Write minimal implementation**

Parse headers into `ActorContext`, require the requested series in `series_ids` or role `showrunner`, reject unknown versions, and inject the context into store methods whose signatures include `series_id` and `version_id`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_auth_context.py tests/test_api_v2.py -v`

Expected: PASS for allowed, forbidden, missing, and unknown-version requests.

- [ ] **Step 5: Commit**

```bash
git add app/auth_context.py app/main.py app/store.py tests/test_auth_context.py tests/test_api_v2.py
git commit -m "feat: authorize series and version API access"
```

## Task 2: Stabilize workflow response envelopes and approval routes

**Files:**
- Modify: `app/main.py`, `app/store.py`
- Test: `tests/test_api_v2.py`, `tests/test_store.py`

**Interfaces:**
- Every JSON response includes `request_id`, `series_id`, and `version_id` where applicable.
- Adds `POST /api/v2/series/{series_id}/versions/{version_id}/issues/{issue_id}/approve`.
- Adds `GET /api/v2/series/{series_id}/versions/{version_id}/audit`.

- [ ] **Step 1: Write the failing test**

```python
def test_approval_is_scoped_and_audited(client):
    response = client.post("/api/v2/series/s1/versions/v1/issues/i1/approve",
                           headers={"X-Series-Ids": "s1", "X-Actor-Id": "writer-1"})
    assert response.status_code == 200
    assert response.json()["request_id"]
    audit = client.get("/api/v2/series/s1/versions/v1/audit", headers={"X-Series-Ids": "s1"})
    assert audit.json()["events"][0]["issue_id"] == "i1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_api_v2.py tests/test_store.py -k approval -v`

Expected: FAIL because approval is not recorded with actor and request metadata.

- [ ] **Step 3: Write minimal implementation**

Create `ApprovalEvent(issue_id, actor_id, action, created_at, request_id)`, append it to the version-scoped audit store, and make repeated approval idempotent while exposing the event history.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_api_v2.py tests/test_store.py -v`

Expected: PASS with stable envelopes, authorization, idempotency, and audit retrieval.

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/store.py tests/test_api_v2.py tests/test_store.py
git commit -m "feat: add audited issue approval workflow"
```

## Task 3: Render complete UI states and evidence workflows

**Files:**
- Modify: `app/static/app.js`, `app/static/index.html`, `app/static/styles.css`
- Test: `tests/test_ui_contract.py`

**Interfaces:**
- Frontend state key is `${seriesId}:${versionId}` and stores `loading`, `error`, `health`, `heatmap`, `evidence`, `comparison`, and `approval`.
- Required controls are health summary, full obligation heatmap, evidence drawer, baseline comparison, cohort panel, discovery results, approve/reject buttons, loading indicators, and retry actions.

- [ ] **Step 1: Write the failing test**

```python
def test_index_contains_all_workflow_panels():
    html = Path("app/static/index.html").read_text()
    for panel_id in ("health-panel", "heatmap-panel", "evidence-drawer", "comparison-panel", "cohort-panel", "discovery-panel"):
        assert f'id="{panel_id}"' in html

def test_frontend_has_error_and_retry_states():
    js = Path("app/static/app.js").read_text()
    assert "loading" in js and "retry" in js and "error" in js
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_ui_contract.py -v`

Expected: FAIL because the current UI omits one or more complete workflow panels and state transitions.

- [ ] **Step 3: Write minimal implementation**

Add semantic panel containers and implement one `loadSeries(seriesId, versionId)` state machine that sets loading before fetch, displays server error with retry, shows an empty state for zero issues, and refreshes the evidence drawer after approval.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_ui_contract.py -v`

Expected: PASS for panel IDs, accessible labels, disclosure copy, and loading/error/retry strings.

- [ ] **Step 5: Commit**

```bash
git add app/static/app.js app/static/index.html app/static/styles.css tests/test_ui_contract.py
git commit -m "feat: complete series health workflow UI"
```

## Task 4: Add API contract coverage for every product surface

**Files:**
- Modify: `app/main.py`
- Test: `tests/test_api_v2.py`

**Interfaces:**
- Routes covered are health, prepublish, handoff, debt board, localization, variants, cohorts, discovery, ingestion status, approval, and audit.
- Each route returns typed error codes `unauthorized`, `not_found`, `validation_error`, or `upstream_unavailable`.

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.parametrize("path", PRODUCT_SURFACE_PATHS)
def test_product_surface_returns_typed_envelope(client, path):
    response = client.get(path, headers={"X-Series-Ids": "s1"})
    assert "request_id" in response.json()
    assert response.status_code in {200, 202, 400, 403, 404, 503}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_api_v2.py -k typed_envelope -v`

Expected: FAIL on routes that still return unstructured demo dictionaries or omit request context.

- [ ] **Step 3: Write minimal implementation**

Wrap each surface in a Pydantic response model, map domain exceptions to the four error codes, and attach the request ID generated by the auth dependency.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_api_v2.py -v`

Expected: PASS for all product routes and failure modes.

- [ ] **Step 5: Commit**

```bash
git add app/main.py tests/test_api_v2.py
git commit -m "feat: stabilize product surface API contracts"
```

## Self-review

- Spec coverage: authorization, per-series/version scoping, approval audit, complete UI panels, loading/error states, and typed product APIs are covered by Tasks 1–4.
- Completeness scan: the plan contains no unfinished marker or vague implementation instruction.
- Type consistency: `ActorContext` authorizes every route, response envelopes carry `request_id`, and frontend state is keyed by the same series/version identifiers.
- Verification: run `uv run --group dev pytest tests/test_auth_context.py tests/test_api_v2.py tests/test_store.py tests/test_ui_contract.py -v`.
