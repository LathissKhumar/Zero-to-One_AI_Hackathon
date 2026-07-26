# Gap 1 — Durable Ingestion Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the demo-only in-memory submission path with durable, resumable fast/deep ingestion for JSON, NDJSON, and uploaded episode files.

**Architecture:** Keep parsing and validation pure, persist immutable submission versions and episode work items behind a repository interface, and drive fast synopsis plus deep extraction through an idempotent coordinator. Fast ingestion publishes a usable ledger first; deep work updates individual episodes and can be retried or cancelled without losing completed work.

**Tech Stack:** Python 3.11–3.14, Pydantic, FastAPI, pytest, Delta/Databricks SQL, `uv`.

## Global Constraints

- Use Python 3.11–3.14 and `uv`.
- New behavior must be developed with pytest red-green-refactor cycles.
- Do not add tests that depend on network access or real credentials.
- Preserve explicit disclosure that product data is user input while demo and training data are synthetic or external training sources.
- Keep extraction calls batchable through Databricks `ai_query`; do not introduce a per-episode network loop as the production path.
- Persist source hashes and immutable version identifiers so a retry cannot silently mutate an earlier version.
- Use `snake_case` functions, `PascalCase` models, explicit type hints, and tested public schemas.

---

## File map

- Create `app/ingestion_models.py`: request, job, episode-work-item, and status models.
- Create `app/ingestion_repository.py`: repository protocol plus in-memory test adapter and Delta adapter boundary.
- Modify `app/ingestion.py`: parsing, submission creation, and coordinator state transitions.
- Modify `app/main.py`: upload, status, cancel, retry, and promotion endpoints.
- Modify `sql/ddl.sql`: durable submission, episode, and job tables.
- Create `scripts/run_ingestion_job.py`: Databricks batch entry point.
- Modify `tests/test_ingestion.py` and create `tests/test_ingestion_api.py`: unit and API coverage.

## Task 1: Define validated submission and job contracts

**Files:**
- Create: `app/ingestion_models.py`
- Test: `tests/test_ingestion.py`

**Interfaces:**
- Produces `parse_submission_json(raw: bytes) -> SubmissionInput`.
- Produces `parse_submission_ndjson(lines: Iterable[bytes]) -> SubmissionInput`.
- Produces `IngestionJob`, `EpisodeWorkItem`, and `IngestionStatus` Pydantic models.

- [ ] **Step 1: Write the failing test**

```python
def test_ndjson_parser_rejects_duplicate_episode_numbers():
    raw = b'{"episode_number": 1, "text": "a"}\n{"episode_number": 1, "text": "b"}\n'
    with pytest.raises(ValueError, match="duplicate episode_number"):
        parse_submission_ndjson(raw.splitlines())

def test_json_parser_normalizes_episode_order():
    result = parse_submission_json(
        b'{"series_id":"s1","episodes":[{"episode_number":2,"text":"b"},{"episode_number":1,"text":"a"}]}'
    )
    assert [episode.episode_number for episode in result.episodes] == [1, 2]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_ingestion.py -k 'ndjson_parser or json_parser' -v`

Expected: FAIL because the parsers and models are not defined.

- [ ] **Step 3: Write minimal implementation**

```python
class SubmissionInput(BaseModel):
    series_id: str
    episodes: list[EpisodeInput]

def parse_submission_ndjson(lines: Iterable[bytes]) -> SubmissionInput:
    episodes = [EpisodeInput.model_validate_json(line) for line in lines if line.strip()]
    numbers = [episode.episode_number for episode in episodes]
    if len(numbers) != len(set(numbers)):
        raise ValueError("duplicate episode_number")
    return SubmissionInput(series_id="uploaded", episodes=sorted(episodes, key=lambda item: item.episode_number))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_ingestion.py -k 'ndjson_parser or json_parser' -v`

Expected: PASS, including empty-line handling and deterministic ordering.

- [ ] **Step 5: Commit**

```bash
git add app/ingestion_models.py tests/test_ingestion.py
git commit -m "feat: define durable ingestion contracts"
```

## Task 2: Persist immutable versions and work items

**Files:**
- Create: `app/ingestion_repository.py`
- Modify: `sql/ddl.sql`
- Test: `tests/test_ingestion.py`

**Interfaces:**
- Produces `SubmissionRepository.create_submission(submission: SubmissionInput, source_hash: str) -> IngestionJob`.
- Produces `SubmissionRepository.list_work_items(job_id: str, stage: str) -> list[EpisodeWorkItem]`.
- Produces `SubmissionRepository.update_work_item(job_id: str, episode_number: int, status: str, error: str | None) -> None`.
- Produces `SubmissionRepository.promote_fast_ledger(job_id: str) -> None`.

- [ ] **Step 1: Write the failing test**

```python
def test_repository_is_idempotent_for_same_source_hash():
    repository = InMemorySubmissionRepository()
    submission = SubmissionInput(series_id="s1", episodes=[EpisodeInput(episode_number=1, text="one")])
    first = repository.create_submission(submission, source_hash="abc")
    second = repository.create_submission(submission, source_hash="abc")
    assert first.job_id == second.job_id
    assert len(repository.list_work_items(first.job_id, "fast")) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_ingestion.py -k idempotent -v`

Expected: FAIL because no repository contract or durable work-item table exists.

- [ ] **Step 3: Write minimal implementation**

Add `canonpulse_submission`, `canonpulse_episode`, and `canonpulse_ingestion_job` Delta tables with primary identifiers `(series_id, version_id)`, `(job_id, episode_number)`, and `job_id`; implement the same contract in the in-memory adapter with a hash-keyed job map.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_ingestion.py -k 'idempotent or work_item' -v`

Expected: PASS with one immutable version and one fast plus one deep work item per episode.

- [ ] **Step 5: Commit**

```bash
git add app/ingestion_repository.py sql/ddl.sql tests/test_ingestion.py
git commit -m "feat: persist ingestion versions and work items"
```

## Task 3: Implement resumable fast/deep coordination

**Files:**
- Modify: `app/ingestion.py`
- Test: `tests/test_ingestion.py`

**Interfaces:**
- Produces `IngestionCoordinator.submit(submission: SubmissionInput) -> IngestionJob`.
- Produces `IngestionCoordinator.run_fast(job_id: str) -> IngestionStatus`.
- Produces `IngestionCoordinator.run_deep(job_id: str, episode_numbers: list[int] | None = None) -> IngestionStatus`.
- Produces `IngestionCoordinator.cancel(job_id: str) -> IngestionStatus` and `retry(job_id: str) -> IngestionStatus`.

- [ ] **Step 1: Write the failing test**

```python
def test_deep_retry_only_reprocesses_failed_items():
    coordinator = make_coordinator(failing_episode_numbers={2})
    job = coordinator.submit(sample_submission(3))
    coordinator.run_fast(job.job_id)
    failed = coordinator.run_deep(job.job_id)
    assert failed.failed_episodes == [2]
    coordinator.extractor.failing_episode_numbers.clear()
    complete = coordinator.retry(job.job_id)
    assert complete.completed_episodes == 3
    assert complete.reprocessed_episodes == [2]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_ingestion.py -k deep_retry -v`

Expected: FAIL because stage transitions and retry filtering are absent.

- [ ] **Step 3: Write minimal implementation**

Implement transitions `queued -> fast_running -> fast_ready -> deep_running -> complete|partial|cancelled`; record `attempt_count`, `started_at`, `finished_at`, and `error`; select only `failed` or `stale` work items during retry.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_ingestion.py -k 'deep_retry or cancel or stale' -v`

Expected: PASS, including cancellation that prevents new work from starting and stale leases that become retryable.

- [ ] **Step 5: Commit**

```bash
git add app/ingestion.py tests/test_ingestion.py
git commit -m "feat: add resumable ingestion coordination"
```

## Task 4: Expose lifecycle endpoints and Databricks batch entry point

**Files:**
- Modify: `app/main.py`
- Create: `scripts/run_ingestion_job.py`
- Create: `tests/test_ingestion_api.py`

**Interfaces:**
- `POST /api/v2/ingestions` accepts JSON, NDJSON, or multipart episode files and returns `IngestionJob` with HTTP 202.
- `GET /api/v2/ingestions/{job_id}` returns `IngestionStatus`.
- `POST /api/v2/ingestions/{job_id}/cancel` and `/retry` return `IngestionStatus`.
- Batch entry point consumes `--job-id` and invokes `run_fast` followed by deep work items.

- [ ] **Step 1: Write the failing test**

```python
def test_ingestion_api_returns_202_and_exposes_progress(client):
    response = client.post("/api/v2/ingestions", json=sample_submission_dict())
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    assert client.get(f"/api/v2/ingestions/{job_id}").json()["status"] == "queued"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_ingestion_api.py -v`

Expected: FAIL with 404 because the lifecycle routes are not registered.

- [ ] **Step 3: Write minimal implementation**

Register routes with dependency-injected coordinator, calculate `sha256` from the raw upload, enqueue fast work synchronously in the local adapter, and make the Databricks script call the repository-backed coordinator without changing the job identifier.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_ingestion_api.py tests/test_ingestion.py -v`

Expected: PASS for JSON, NDJSON, status, cancel, retry, and invalid duplicate episodes.

- [ ] **Step 5: Commit**

```bash
git add app/main.py scripts/run_ingestion_job.py tests/test_ingestion_api.py
git commit -m "feat: expose ingestion lifecycle API"
```

## Self-review

- Spec coverage: two-speed ingest, durable versions, batch work items, retries, cancellation, stale recovery, JSON/NDJSON/upload parsing, API visibility, and Databricks entry point are covered by Tasks 1–4.
- Completeness scan: the plan contains no unfinished marker or vague implementation instruction.
- Type consistency: `SubmissionInput`, `IngestionJob`, `IngestionStatus`, `EpisodeWorkItem`, and repository/coordinator method signatures are used consistently across tasks.
- Verification: run `uv run --group dev pytest tests/test_ingestion.py tests/test_ingestion_api.py -v` before moving to Gap 2.
