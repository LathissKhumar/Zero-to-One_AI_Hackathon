# CanonPulse Gap Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the gaps found in the CanonPulse spec audit — orphaned code, faked stubs, partial implementations — including real OpenAI-backed LLM paths for personas, cohort-style repair text, and deep ingestion extraction.

**Architecture:** Every new LLM-calling path reuses the existing `app/llm_extractor.py` machinery (`_http_transport`, `cache_key`, `backend_for`, disk-cached responses) rather than inventing a second HTTP client. Every LLM path stays **opt-in behind `OPENAI_API_KEY` presence** — when the key is absent, code falls back to (or refuses with a clear 422, never silently fakes) the existing deterministic/heuristic behavior, matching the honesty convention already used by `app/predictor.py` and `app/extraction.py`.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, pytest, `python-dotenv` (new), OpenAI chat-completions HTTP API (no SDK — same raw-`urllib` approach `app/llm_extractor.py` already uses).

## Global Constraints

- Python `>=3.11,<3.15` (pyproject.toml).
- New runtime dependency must be added to `pyproject.toml` `[project.dependencies]`, matching existing version-pin style (`"name>=X,<Y"`).
- No real network calls in `pytest` — every test that exercises an LLM-calling function injects a fake `transport` callable, exactly like `tests/test_llm_extractor.py` already does.
- `.env` holds `OPENAI_API_KEY` (present) and is already gitignored — never print, log, or write this value anywhere other than the process environment.
- Every commit message: short imperative summary + `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>` trailer (repo convention from recent commits).
- Run `.venv/bin/python -m pytest tests/ -q` after every task; do not proceed to the next task on red.

---

### Task 0: Load `.env` and add an OpenAI config helper

**Files:**
- Modify: `pyproject.toml`
- Create: `app/llm_config.py`
- Test: `tests/test_llm_config.py`
- Modify: `app/main.py:1-15` (add `load_dotenv()` call)

**Interfaces:**
- Produces: `app.llm_config.openai_config() -> OpenAIConfig | None` where `OpenAIConfig` is a small dataclass with fields `endpoint: str`, `token: str`, `model: str`. Returns `None` when `OPENAI_API_KEY` is unset. Every later task that needs OpenAI calls this function — never reads `os.environ["OPENAI_API_KEY"]` directly outside this module.

- [ ] **Step 1: Add the dependency**

Edit `pyproject.toml`, in `[project] dependencies`, add one line after `"pyyaml>=6.0,<7",`:

```toml
  "python-dotenv>=1.0,<2",
```

Install it:

```bash
.venv/bin/pip install "python-dotenv>=1.0,<2"
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_llm_config.py`:

```python
from __future__ import annotations

import os

from app.llm_config import openai_config


def test_openai_config_is_none_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert openai_config() is None


def test_openai_config_reads_key_and_defaults_model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    config = openai_config()
    assert config is not None
    assert config.token == "sk-test-123"
    assert config.model == "gpt-4o-mini"
    assert config.endpoint == "https://api.openai.com/v1/chat/completions"


def test_openai_config_honours_model_override(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    config = openai_config()
    assert config.model == "gpt-4o"
```

- [ ] **Step 2b: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_llm_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.llm_config'`

- [ ] **Step 3: Write the implementation**

Create `app/llm_config.py`:

```python
"""Single place that reads OPENAI_API_KEY -- nothing else reads it directly.

Every LLM-backed feature in this app (personas, repair text, deep ingestion
extraction) is opt-in: present when this returns a config, silently absent
(falling back to the deterministic/heuristic path) or explicitly refused
(422, never faked) when it returns None. See docs/superpowers/specs/
2026-07-26-canonpulse-gap-closure-design.md for which behaviour applies where.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

_DEFAULT_MODEL = "gpt-4o-mini"
_DEFAULT_ENDPOINT = "https://api.openai.com/v1/chat/completions"


@dataclass(frozen=True)
class OpenAIConfig:
    endpoint: str
    token: str
    model: str


def openai_config() -> OpenAIConfig | None:
    token = os.environ.get("OPENAI_API_KEY")
    if not token:
        return None
    return OpenAIConfig(
        endpoint=os.environ.get("OPENAI_BASE_URL", _DEFAULT_ENDPOINT),
        token=token,
        model=os.environ.get("OPENAI_MODEL", _DEFAULT_MODEL),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_llm_config.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Load `.env` at process start**

Modify `app/main.py`, right after the `from __future__ import annotations` line and before other imports (so env vars are set before anything reads them):

```python
from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

import os
```

(Keep every existing import below unchanged.)

- [ ] **Step 6: Run full suite and commit**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: all passing (no regressions)

```bash
git add pyproject.toml app/llm_config.py tests/test_llm_config.py app/main.py
git commit -m "$(cat <<'EOF'
feat: add OpenAI config helper and load .env at startup

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 1: Repository support for accumulated extraction results

**Files:**
- Modify: `app/ingestion_repository.py`
- Test: `tests/test_ingestion_contracts.py` (add new tests, keep existing ones passing)

**Interfaces:**
- Consumes: `app.extraction.ExtractionResult` (existing: `nodes`, `entries`, `payoffs`, `excerpts`, `rejected`, `backend`).
- Produces: `SubmissionRepository.record_extraction(job_id: str, episode_number: int, stage: str, result: ExtractionResult) -> None` and `SubmissionRepository.accumulated_result(job_id: str, stage: str) -> ExtractionResult`, both on the Protocol and on `InMemorySubmissionRepository`. Task 2 calls these.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_ingestion_contracts.py`:

```python
from app.extraction import ExtractionResult
from app.narrative_models import NarrativeNode


def test_repository_accumulates_extraction_results_per_stage():
    repository = InMemorySubmissionRepository()
    submission = SubmissionInput(
        series_id="s1",
        title="S",
        genre="thriller",
        episodes=[EpisodeInput(episode_number=1, text="one"), EpisodeInput(episode_number=2, text="two")],
    )
    job = repository.create_submission(submission, source_hash="abc")

    repository.record_extraction(
        job.job_id, 1, "deep",
        ExtractionResult(nodes=[NarrativeNode(id="n1", episode=1, perceived_index=1, summary="a")]),
    )
    repository.record_extraction(
        job.job_id, 2, "deep",
        ExtractionResult(nodes=[NarrativeNode(id="n2", episode=2, perceived_index=2, summary="b")], rejected=1),
    )

    accumulated = repository.accumulated_result(job.job_id, "deep")
    assert [node.id for node in accumulated.nodes] == ["n1", "n2"]
    assert accumulated.rejected == 1

    empty = repository.accumulated_result(job.job_id, "fast")
    assert empty.nodes == []
    assert empty.rejected == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_ingestion_contracts.py::test_repository_accumulates_extraction_results_per_stage -v`
Expected: FAIL with `AttributeError: 'InMemorySubmissionRepository' object has no attribute 'record_extraction'`

- [ ] **Step 3: Implement**

Modify `app/ingestion_repository.py`:

```python
"""Persistence boundary for immutable submission versions and work items."""

from __future__ import annotations

import hashlib
from typing import Protocol

from app.extraction import ExtractionResult
from app.ingestion_models import EpisodeWorkItem, IngestionJob, SubmissionInput


class SubmissionRepository(Protocol):
    def create_submission(self, submission: SubmissionInput, source_hash: str) -> IngestionJob: ...

    def list_work_items(self, job_id: str, stage: str) -> list[EpisodeWorkItem]: ...

    def update_work_item(self, job_id: str, episode_number: int, stage: str, status: str, error: str | None = None) -> None: ...

    def promote_fast_ledger(self, job_id: str) -> None: ...

    def record_extraction(self, job_id: str, episode_number: int, stage: str, result: ExtractionResult) -> None: ...

    def accumulated_result(self, job_id: str, stage: str) -> ExtractionResult: ...


class InMemorySubmissionRepository:
    """Deterministic adapter for local mode and unit tests."""

    def __init__(self) -> None:
        self.jobs: dict[str, IngestionJob] = {}
        self.work_items: dict[tuple[str, int, str], EpisodeWorkItem] = {}
        self._source_jobs: dict[tuple[str, str], str] = {}
        self._extractions: dict[tuple[str, str], ExtractionResult] = {}

    def create_submission(self, submission: SubmissionInput, source_hash: str) -> IngestionJob:
        key = (submission.series_id, source_hash)
        if key in self._source_jobs:
            return self.jobs[self._source_jobs[key]].model_copy(deep=True)
        digest = hashlib.sha256(f"{submission.series_id}:{source_hash}".encode()).hexdigest()[:16]
        job = IngestionJob(job_id=digest, series_id=submission.series_id, source_hash=source_hash)
        self.jobs[job.job_id] = job
        self._source_jobs[key] = job.job_id
        for episode in submission.episodes:
            for stage in ("fast", "deep"):
                item = EpisodeWorkItem(job_id=job.job_id, episode_number=episode.episode_number, stage=stage)
                self.work_items[(job.job_id, episode.episode_number, stage)] = item
        return job.model_copy(deep=True)

    def list_work_items(self, job_id: str, stage: str) -> list[EpisodeWorkItem]:
        return [
            item.model_copy(deep=True)
            for (item_job, _episode, item_stage), item in sorted(self.work_items.items())
            if item_job == job_id and item_stage == stage
        ]

    def update_work_item(self, job_id: str, episode_number: int, stage: str, status: str, error: str | None = None) -> None:
        key = (job_id, episode_number, stage)
        item = self.work_items[key]
        item.status = status
        item.error = error
        if status == "running":
            item.attempt_count += 1

    def promote_fast_ledger(self, job_id: str) -> None:
        job = self.jobs[job_id]
        job.status = "fast_ready"

    def record_extraction(self, job_id: str, episode_number: int, stage: str, result: ExtractionResult) -> None:
        key = (job_id, stage)
        existing = self._extractions.get(key)
        if existing is None:
            self._extractions[key] = result.model_copy(deep=True)
            return
        existing.nodes.extend(result.nodes)
        existing.entries.extend(result.entries)
        existing.payoffs.extend(result.payoffs)
        existing.excerpts.extend(result.excerpts)
        existing.rejected += result.rejected

    def accumulated_result(self, job_id: str, stage: str) -> ExtractionResult:
        return self._extractions.get((job_id, stage), ExtractionResult()).model_copy(deep=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_ingestion_contracts.py -v`
Expected: all PASS, including the new test

- [ ] **Step 5: Commit**

```bash
git add app/ingestion_repository.py tests/test_ingestion_contracts.py
git commit -m "$(cat <<'EOF'
feat: accumulate per-episode extraction results in the ingestion repository

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Real fast/deep extractor for `IngestionCoordinator`, plus `series()` assembly

**Files:**
- Modify: `app/ingestion.py`
- Test: `tests/test_ingestion_contracts.py`

**Interfaces:**
- Consumes: `SubmissionRepository.record_extraction`/`accumulated_result` (Task 1), `app.heuristic_extractor.HeuristicExtractor`, `app.llm_extractor.LLMExtractor`, `app.llm_config.openai_config` (Task 0).
- Produces: `RealIngestionExtractor(repository, openai_config=None)` with `extract_fast(episode, job_id)` / `extract_deep(episode, job_id)`; `IngestionCoordinator.series(job_id, stage="deep") -> Series`. Main.py (Task 3) wires this in.

Note: this task changes the extractor call signature from `extract_fast(self, episode)` to `extract_fast(self, episode, job_id)` (same for `extract_deep`). This requires updating `_DefaultIngestionExtractor` and the existing `_Extractor` test double in `tests/test_ingestion_contracts.py`.

- [ ] **Step 1: Update the existing test double's signature (keep old tests green)**

Modify `tests/test_ingestion_contracts.py`, replace the `_Extractor` class:

```python
class _Extractor:
    def __init__(self, failing_episode_numbers: set[int] | None = None):
        self.failing_episode_numbers = failing_episode_numbers or set()

    def extract_fast(self, episode: EpisodeInput, job_id: str) -> None:
        return None

    def extract_deep(self, episode: EpisodeInput, job_id: str) -> None:
        if episode.episode_number in self.failing_episode_numbers:
            raise TimeoutError("temporary extraction failure")
```

- [ ] **Step 2: Write the failing tests for the new behavior**

Add to `tests/test_ingestion_contracts.py`:

```python
from app.ingestion import RealIngestionExtractor
from app.narrative_models import Series


def test_real_extractor_fills_fast_stage_from_synopsis_with_scaled_confidence():
    repository = InMemorySubmissionRepository()
    submission = SubmissionInput(
        series_id="s1", title="S", genre="thriller",
        episodes=[EpisodeInput(episode_number=1, text="Full body text.", synopsis="Ana promises to return.")],
    )
    job = repository.create_submission(submission, source_hash="abc")
    extractor = RealIngestionExtractor(repository)

    extractor.extract_fast(submission.episodes[0], job.job_id)

    result = repository.accumulated_result(job.job_id, "fast")
    assert len(result.entries) >= 1
    assert all(entry.confidence == 0.4 for entry in result.entries)


def test_real_extractor_deep_stage_falls_back_to_heuristic_without_openai_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    repository = InMemorySubmissionRepository()
    submission = SubmissionInput(
        series_id="s1", title="S", genre="thriller",
        episodes=[EpisodeInput(episode_number=1, text="Ana promises to return to the ferry.")],
    )
    job = repository.create_submission(submission, source_hash="abc")
    extractor = RealIngestionExtractor(repository)

    extractor.extract_deep(submission.episodes[0], job.job_id)

    result = repository.accumulated_result(job.job_id, "deep")
    assert result.backend is None  # HeuristicExtractor sets no backend label


def test_real_extractor_deep_stage_uses_llm_when_openai_key_present(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    def fake_transport(*, endpoint, token, model, prompt):
        return '{"nodes": [], "entries": [], "payoffs": [], "excerpts": []}'

    repository = InMemorySubmissionRepository()
    submission = SubmissionInput(
        series_id="s1", title="S", genre="thriller",
        episodes=[EpisodeInput(episode_number=1, text="Ana promises to return.")],
    )
    job = repository.create_submission(submission, source_hash="abc")
    extractor = RealIngestionExtractor(repository, transport=fake_transport)

    extractor.extract_deep(submission.episodes[0], job.job_id)

    result = repository.accumulated_result(job.job_id, "deep")
    assert result.backend == "openai"


def test_coordinator_series_assembles_from_accumulated_deep_result():
    repository = InMemorySubmissionRepository()
    submission = SubmissionInput(
        series_id="s1", title="S", genre="thriller",
        episodes=[EpisodeInput(episode_number=1, text="Ana promises to return to the ferry.")],
    )
    coordinator = IngestionCoordinator(repository=repository, extractor=RealIngestionExtractor(repository))
    job = coordinator.submit(submission)
    coordinator.run_fast(job.job_id)
    coordinator.run_deep(job.job_id)

    series = coordinator.series(job.job_id)
    assert isinstance(series, Series)
    assert series.id == "s1"
    assert series.total_episodes == 1
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_ingestion_contracts.py -v`
Expected: FAIL — `RealIngestionExtractor` / `IngestionCoordinator.series` do not exist yet; old tests still pass.

- [ ] **Step 4: Implement**

Modify `app/ingestion.py`. First, add imports near the top (after existing imports):

```python
from app.extraction import ExtractionResult
from app.llm_config import openai_config
from app.llm_extractor import LLMExtractor, Transport
```

Then add, after the `SynopsisExtractor` class and before `IngestionCoordinator`:

```python
class RealIngestionExtractor:
    """Fast/deep extractor wired into IngestionCoordinator's real lifecycle.

    Fast stays HeuristicExtractor-over-synopsis-only (confidence-scaled), same
    as SynopsisExtractor. Deep uses LLMExtractor (OpenAI) when OPENAI_API_KEY
    is configured; otherwise it falls back to HeuristicExtractor over the full
    body -- degraded, never faked, and ExtractionResult.backend (None for
    Heuristic, "openai" for LLMExtractor) tells a caller which one ran.
    """

    def __init__(self, repository: SubmissionRepository, transport: Transport | None = None) -> None:
        self._repository = repository
        self._transport = transport

    def extract_fast(self, episode: EpisodeInput, job_id: str) -> None:
        result = HeuristicExtractor().extract(
            [{"episode": episode.episode_number, "synopsis": episode.synopsis or ""}]
        )
        for entry in result.entries:
            entry.confidence = 0.4
        self._repository.record_extraction(job_id, episode.episode_number, "fast", result)

    def extract_deep(self, episode: EpisodeInput, job_id: str) -> None:
        config = openai_config()
        rows = [{"episode": episode.episode_number, "body": episode.text}]
        if config is None:
            result = HeuristicExtractor().extract(rows)
        else:
            result = LLMExtractor(
                endpoint=config.endpoint,
                token=config.token,
                model=config.model,
                cache_path="data/extraction_cache/deep_ingest_openai.json",
                transport=self._transport,
            ).extract(rows)
        self._repository.record_extraction(job_id, episode.episode_number, "deep", result)
```

Now update `_series_from_result` usage: `IngestionCoordinator` needs its own assembly helper because `SubmissionInput`/`EpisodeInput` use `episode_number`, not the older `Submission`/`SubmissionEpisode`'s `episode`. Add this function near the top of the file, after `_series_from_result`:

```python
def _series_from_submission_input(submission: SubmissionInput, result: ExtractionResult, *, source_version: str) -> Series:
    writer_map = {str(episode.episode_number): episode.writer_id for episode in submission.episodes}
    language_map = {str(episode.episode_number): episode.language for episode in submission.episodes}
    return Series(
        id=submission.series_id,
        title=submission.title,
        genre=submission.genre,
        total_episodes=max(episode.episode_number for episode in submission.episodes),
        ongoing=submission.ongoing,
        nodes=result.nodes,
        entries=result.entries,
        payoffs=result.payoffs,
        excerpts=result.excerpts,
        source_version=source_version,
        episode_writers=writer_map,
        episode_languages=language_map,
    )
```

Finally, add a `series` method to `IngestionCoordinator` (place it right after `cancel`):

```python
    def series(self, job_id: str, stage: str = "deep") -> Series:
        submission = self._submissions[job_id]
        result = self.repository.accumulated_result(job_id, stage)
        source_version = hashlib.sha256(f"{job_id}:{stage}".encode()).hexdigest()
        return _series_from_submission_input(submission, result, source_version=source_version)
```

`hashlib` is already imported at the top of `app/ingestion.py`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_ingestion_contracts.py -v`
Expected: all PASS

- [ ] **Step 6: Run full suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: all PASS (no regressions in `test_ingestion.py`, `test_ingestion_api.py` which use the unrelated `IngestService`/`_DefaultIngestionExtractor` path — those are untouched)

- [ ] **Step 7: Commit**

```bash
git add app/ingestion.py tests/test_ingestion_contracts.py
git commit -m "$(cat <<'EOF'
feat: wire real heuristic/LLM extractors into IngestionCoordinator

Deep stage now uses OpenAI (LLMExtractor) when OPENAI_API_KEY is
configured and falls back to HeuristicExtractor otherwise -- the
previous _DefaultIngestionExtractor was a no-op that produced no graph
at all. Adds IngestionCoordinator.series() to assemble the resulting
Series from accumulated per-episode extraction.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Wire the real extractor and a series-fetch route into `main.py`; wire orphaned `document_ingestion.py`

**Files:**
- Modify: `app/main.py`
- Test: `tests/test_ingestion_api.py`

**Interfaces:**
- Consumes: `IngestionCoordinator(repository, extractor=RealIngestionExtractor(repository))` (Task 2), `app.document_ingestion.normalize_parsed_document` (existing, untouched).
- Produces: `GET /api/v2/ingestions/{job_id}/series`, `POST /api/ingest/document`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_ingestion_api.py` (check the file's existing imports first; it already builds a `TestClient(create_app())` — follow that pattern):

```python
def test_document_ingest_route_creates_a_submission(client):
    payload = {
        "parsed": {
            "document": {
                "elements": [
                    {"id": 0, "type": "section_header", "content": "Episode 1", "bbox": [{"page_id": 0}]},
                    {"id": 1, "type": "text", "content": "Rain covered the station.", "bbox": [{"page_id": 0}]},
                ]
            }
        },
        "source_path": "/Volumes/writers/raw/monsoon.docx",
        "series_id": "monsoon-doc",
        "title": "The Monsoon",
        "genre": "drama",
    }
    response = client.post("/api/ingest/document", json=payload)
    assert response.status_code == 202
    body = response.json()
    assert body["review_required"] is False
    assert body["job"]["series_id"] == "monsoon-doc"


def test_document_ingest_route_reports_review_required():
    from fastapi.testclient import TestClient
    from app.main import create_app

    client = TestClient(create_app())
    payload = {
        "parsed": {"document": {"elements": [{"id": 1, "type": "text", "content": "A single episode."}]}},
        "source_path": "/Volumes/writers/raw/upload.docx",
        "series_id": "monsoon-doc-2",
        "title": "The Monsoon",
        "genre": "drama",
    }
    response = client.post("/api/ingest/document", json=payload)
    assert response.status_code == 202
    assert response.json()["review_required"] is True


def test_ingestion_series_route_returns_assembled_series():
    from fastapi.testclient import TestClient
    from app.main import create_app

    client = TestClient(create_app())
    submission = {
        "series_id": "s-series-route",
        "title": "S",
        "genre": "thriller",
        "episodes": [{"episode_number": 1, "text": "Ana promises to return to the ferry."}],
    }
    created = client.post("/api/v2/ingestions", json=submission)
    job_id = created.json()["job_id"]
    client.post(f"/api/v2/ingestions/{job_id}/cancel")  # no-op sanity call, coordinator must survive it
    response = client.get(f"/api/v2/ingestions/{job_id}/series")
    assert response.status_code == 200
    assert response.json()["id"] == "s-series-route"
```

(If `tests/test_ingestion_api.py` has no `client` fixture, use the `TestClient(create_app())` inline pattern shown in the last two tests for all three instead — check the file first and match its existing style exactly.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_ingestion_api.py -v`
Expected: FAIL — 404s, routes don't exist yet.

- [ ] **Step 3: Implement**

Modify `app/main.py`. Add imports (near the existing `from app.ingestion import ...` line):

```python
from app.document_ingestion import normalize_parsed_document
from app.ingestion import IngestJob, IngestService, IngestionCoordinator, RealIngestionExtractor, Submission
from app.ingestion_repository import InMemorySubmissionRepository
```

(Replace the existing `from app.ingestion import IngestJob, IngestService, IngestionCoordinator, Submission` line with the updated one above.)

Add a request model near the other `*Request` classes (after `LocalizationRequest`):

```python
class DocumentIngestRequest(BaseModel):
    parsed: dict
    source_path: str
    series_id: str
    title: str
    genre: str
    language: str = "en"
    ongoing: bool = True
```

Change how `ingestion_coordinator` is constructed inside `create_app()` — find:

```python
    ingest_service = IngestService()
    ingestion_coordinator = IngestionCoordinator()
```

Replace with:

```python
    ingest_service = IngestService()
    _ingestion_repository = InMemorySubmissionRepository()
    ingestion_coordinator = IngestionCoordinator(
        repository=_ingestion_repository,
        extractor=RealIngestionExtractor(_ingestion_repository),
    )
```

Add two routes right after `retry_ingestion` (after the existing `/api/v2/ingestions/{job_id}/retry` route):

```python
    @app.get("/api/v2/ingestions/{job_id}/series")
    def ingestion_series(job_id: str) -> dict:
        try:
            return ingestion_coordinator.series(job_id).model_dump()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/ingest/document", status_code=202)
    def ingest_document(payload: DocumentIngestRequest) -> dict:
        try:
            normalized = normalize_parsed_document(
                payload.parsed,
                source_path=payload.source_path,
                series_id=payload.series_id,
                title=payload.title,
                genre=payload.genre,
                ongoing=payload.ongoing,
                language=payload.language,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        submission_input = SubmissionInput(
            series_id=normalized.submission.series_id,
            title=normalized.submission.title,
            genre=normalized.submission.genre,
            episodes=normalized.submission.episodes,
            ongoing=normalized.submission.ongoing,
        )
        job = ingestion_coordinator.submit(submission_input)
        return {
            "job": job.model_dump(mode="json"),
            "review_required": normalized.review_required,
            "warnings": normalized.warnings,
        }
```

`SubmissionInput` is already imported in `main.py` (`from app.ingestion_models import IngestionJob, IngestionStatus, SubmissionInput`) — no new import needed for it. `normalized.submission` from `normalize_parsed_document` is already a `SubmissionInput`, so the explicit reconstruction above is redundant — simplify to:

```python
        job = ingestion_coordinator.submit(normalized.submission)
```

(Use this simpler line instead of rebuilding `submission_input`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_ingestion_api.py -v`
Expected: all PASS

- [ ] **Step 5: Run full suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add app/main.py tests/test_ingestion_api.py
git commit -m "$(cat <<'EOF'
feat: wire document ingestion and real extraction into the API

POST /api/ingest/document turns ai_parse_document output into a
submission via the previously-orphaned normalize_parsed_document.
GET /api/v2/ingestions/{job_id}/series exposes the graph the real
fast/deep extractors (Task 2) actually build.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Rename personas to spec names; add real OpenAI-backed persona handler

**Files:**
- Modify: `app/personas.py`
- Create: `app/llm_agents.py`
- Test: `tests/test_personas.py`, `tests/test_llm_agents.py`
- Modify: `app/main.py` (writers-room route)

**Interfaces:**
- Consumes: `app.llm_config.openai_config` (Task 0), `app.llm_extractor._http_transport`, `cache_key`, `backend_for`, `parse_extraction_row` (existing, reused not duplicated).
- Produces: `PERSONAS` (renamed ids/names), `app.llm_agents.LLMPersonaHandler` — a callable matching `AgentRunner`'s `handler: Callable` contract (`(persona, graph, budget) -> dict`).

- [ ] **Step 1: Rename personas**

Modify `app/personas.py`, replace the `PERSONAS` tuple:

```python
PERSONAS: tuple[Persona, ...] = (
    Persona(id="director", name="Director", focus="macro narrative pacing and structural vision"),
    Persona(id="editor", name="Editor", focus="prose tightness, dialogue flow, and scene transitions"),
    Persona(id="critic", name="Critic", focus="cliches, tropes, and narrative logic gaps"),
    Persona(id="psychologist", name="Psychologist", focus="character motivation and emotional logic"),
    Persona(id="historian", name="Historian", focus="lore consistency, world-building rules, and continuity across languages"),
)
```

- [ ] **Step 2: Run existing tests to confirm the rename alone doesn't break anything**

Run: `.venv/bin/python -m pytest tests/test_personas.py tests/test_api_v2.py -v`
Expected: PASS (neither test hardcodes the old ids — `test_personas.py` builds its own `Persona` objects, `test_api_v2.py` only checks `len(annotations) == 5`)

- [ ] **Step 3: Write the failing test for the LLM handler**

Create `tests/test_llm_agents.py`:

```python
from __future__ import annotations

import json

from app.llm_agents import LLMPersonaHandler
from app.personas import PERSONAS
from tests.test_variants import _series


def test_llm_persona_handler_returns_no_issues_when_nothing_open():
    def fake_transport(*, endpoint, token, model, prompt):
        raise AssertionError("must not call the model when there is nothing open")

    handler = LLMPersonaHandler(endpoint="https://api.openai.com/v1/chat/completions", token="sk-test", model="gpt-4o-mini", transport=fake_transport)
    series = _series()
    # Push the horizon to episode 1 so nothing has had a chance to open yet
    result = handler(PERSONAS[0], series.model_copy(update={"total_episodes": 1}), budget=512)
    assert result["persona_id"] == "director"
    assert result["timed_out"] is False


def test_llm_persona_handler_parses_model_json_into_annotation_fields():
    calls = []

    def fake_transport(*, endpoint, token, model, prompt):
        calls.append(prompt)
        return json.dumps({"issue_ids": ["some-issue"], "confidence": 0.83, "reason_codes": ["fairness_risk"]})

    handler = LLMPersonaHandler(endpoint="https://api.openai.com/v1/chat/completions", token="sk-test", model="gpt-4o-mini", transport=fake_transport)
    series = _series()
    result = handler(PERSONAS[2], series, budget=512)

    assert result["confidence"] == 0.83
    assert result["reason_codes"] == ("fairness_risk",)
    assert result["persona_id"] == "critic"
    assert len(calls) == 1
    assert "Critic" in calls[0] or "cliche" in calls[0].lower()


def test_llm_persona_handler_falls_back_when_model_returns_malformed_json():
    def fake_transport(*, endpoint, token, model, prompt):
        return "not json"

    handler = LLMPersonaHandler(endpoint="https://api.openai.com/v1/chat/completions", token="sk-test", model="gpt-4o-mini", transport=fake_transport)
    series = _series()
    result = handler(PERSONAS[1], series, budget=512)

    assert result["confidence"] == 0.0
    assert result["reason_codes"] == ("malformed_model_output",)
```

First check `tests/test_variants.py::_series` builds a `Series` with at least one open obligation by episode `total_episodes` — read that fixture before relying on it; if it has no open obligations at all, adjust the second/third test to call `LedgerResolver().resolve_series` directly to pick a real `entry.id`/`description` instead of assuming one exists blindly. Confirm with:

```bash
.venv/bin/python -c "
from app.ledger import LedgerResolver
from tests.test_variants import _series
s = _series()
print([item.entry.id for item in LedgerResolver().resolve_series(s) if item.state != 'paid'])
"
```

Adjust the tests' assumptions to match whatever this prints (there must be at least one non-paid entry for tests 2 and 3 to exercise the "found an issue" path — if the fixture has none, use `series.model_copy(update={"total_episodes": <a smaller number known to have an open entry>})`).

- [ ] **Step 4: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_llm_agents.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.llm_agents'`

- [ ] **Step 5: Implement**

Create `app/llm_agents.py`:

```python
"""OpenAI-backed Writers Room persona handler and repair-text generation.

Both reuse app.llm_extractor's transport/cache-key/backend-label machinery
rather than a second HTTP client. Both are opt-in: callers only construct
these when app.llm_config.openai_config() returns non-None; the deterministic
paths in app.personas and app.variants remain the default everywhere else.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.extraction import parse_extraction_row
from app.ledger import LedgerResolver
from app.llm_extractor import Transport, _http_transport, backend_for, cache_key
from app.narrative_models import Series
from app.personas import Persona

_PERSONA_PROMPT = (
    "You are the {name} in a serialized fiction Writers Room. Your focus is "
    "{focus}. Review this open story obligation and respond with JSON only, "
    "no prose, no markdown fences: "
    '{{"issue_ids": ["{issue_id}"], "confidence": <float 0-1>, '
    '"reason_codes": ["<short_snake_case_code>", ...]}}. '
    "Obligation: {description}"
)


class LLMPersonaHandler:
    """Callable matching AgentRunner's `handler(persona, graph, budget) -> dict`."""

    def __init__(self, endpoint: str, token: str, model: str, cache_path: str | Path | None = None, transport: Transport | None = None) -> None:
        self._endpoint = endpoint
        self._token = token
        self._model = model
        self._transport = transport or _http_transport
        self.backend = backend_for(endpoint)
        self._cache_path = Path(cache_path) if cache_path else None
        self._cache: dict[str, str] = {}
        if self._cache_path and self._cache_path.exists():
            self._cache = json.loads(self._cache_path.read_text(encoding="utf-8"))

    def __call__(self, persona: Persona, graph: Series, budget: int) -> dict:
        resolved = [item for item in LedgerResolver().resolve_series(graph) if item.state != "paid"]
        if not resolved:
            return {
                "persona_id": persona.id,
                "issue_ids": (),
                "confidence": 0.0,
                "reason_codes": ("no_open_obligations",),
                "latency_ms": 0.0,
                "timed_out": False,
            }
        item = resolved[0]
        prompt = _PERSONA_PROMPT.format(
            name=persona.name, focus=persona.focus, issue_id=item.entry.id, description=item.entry.description
        )
        key = cache_key(self._model, prompt)
        if key in self._cache:
            raw = self._cache[key]
        else:
            raw = self._transport(endpoint=self._endpoint, token=self._token, model=self._model, prompt=prompt)
            self._cache[key] = raw
            if self._cache_path is not None:
                self._cache_path.parent.mkdir(parents=True, exist_ok=True)
                self._cache_path.write_text(json.dumps(self._cache, indent=2, sort_keys=True), encoding="utf-8")

        parsed = parse_extraction_row(raw)
        if parsed is None:
            return {
                "persona_id": persona.id,
                "issue_ids": (item.entry.id,),
                "confidence": 0.0,
                "reason_codes": ("malformed_model_output",),
                "latency_ms": 0.0,
                "timed_out": False,
            }
        return {
            "persona_id": persona.id,
            "issue_ids": tuple(parsed.get("issue_ids", [item.entry.id])),
            "confidence": float(parsed.get("confidence", 0.5)),
            "reason_codes": tuple(parsed.get("reason_codes", ["llm_review"])) or ("llm_review",),
            "latency_ms": 0.0,
            "timed_out": False,
        }
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_llm_agents.py -v`
Expected: all PASS (adjust fixture assumptions per Step 3's note if needed, then re-run)

- [ ] **Step 7: Wire an opt-in LLM path into `/api/writers-room`**

Modify `app/main.py`. Add import:

```python
from app.llm_agents import LLMPersonaHandler
from app.llm_config import openai_config
from app.personas import AgentRunner, PERSONAS, WritersRoom, run_writers_room
```

(Replace the existing `from app.personas import WritersRoom` line with the block above.)

Replace the `/api/writers-room` route:

```python
    @app.get("/api/writers-room")
    def writers_room(episode: int | None = Query(default=None, ge=1), use_llm: bool = Query(default=False)) -> dict:
        current = _series()
        if not use_llm:
            return {"series_id": current.id, "backend": "deterministic-structured", "annotations": [item.model_dump() for item in WritersRoom().review(current, episode)]}

        config = openai_config()
        if config is None:
            raise HTTPException(status_code=422, detail="use_llm=true requires OPENAI_API_KEY to be configured")
        handler = LLMPersonaHandler(
            endpoint=config.endpoint, token=config.token, model=config.model,
            cache_path="data/extraction_cache/writers_room_openai.json",
        )
        result = run_writers_room(current, PERSONAS, runner=AgentRunner(handler))
        return {
            "series_id": current.id,
            "backend": handler.backend,
            "annotations": [annotation.model_dump() for annotation in result.annotations],
            "timeouts": result.timeouts,
            "disagreements": [item.model_dump() for item in result.disagreements],
        }
```

- [ ] **Step 8: Write a route-level test for the opt-in path**

Add to `tests/test_api_v2.py` (near the existing `test_...writers-room...` test):

```python
def test_writers_room_llm_path_requires_openai_key(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.get("/api/writers-room", params={"use_llm": True})
    assert response.status_code == 422
```

(If `test_api_v2.py` has no `monkeypatch`-accepting `client` fixture pattern, use `from fastapi.testclient import TestClient; from app.main import create_app; client = TestClient(create_app())` inline instead, matching whatever style the file already uses — check it first.)

- [ ] **Step 9: Run full suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: all PASS

- [ ] **Step 10: Commit**

```bash
git add app/personas.py app/llm_agents.py tests/test_llm_agents.py app/main.py tests/test_api_v2.py
git commit -m "$(cat <<'EOF'
feat: rename personas to spec names, add real OpenAI-backed persona handler

Writers Room personas were named Continuity Editor/Mystery Architect/
Emotional Arc Editor/Serial Showrunner/Localization Editor and never
called a model. Renamed to the spec's Director/Editor/Critic/
Psychologist/Historian and added an opt-in use_llm=true path on
/api/writers-room backed by a real OpenAI call; default stays the
deterministic path.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Rename cohorts to spec names; add a dormant Databricks-shaped cohort path

**Files:**
- Modify: `app/cohorts.py`
- Test: `tests/test_cohorts.py`

**Interfaces:**
- Produces: `COHORTS` (renamed ids/names, weights preserved in spirit), `databricks_cohort_reaction(...)` (new, not wired to any route — no Databricks credentials exist in this environment; this closes the "no code path exists at all" gap without pretending it runs).

- [ ] **Step 1: Update the existing test's weight-diversity assumption first (should still pass unchanged)**

Run: `.venv/bin/python -m pytest tests/test_cohorts.py -v` to confirm current green baseline before editing.

- [ ] **Step 2: Rename cohorts**

Modify `app/cohorts.py`, replace the `COHORTS` tuple:

```python
COHORTS: tuple[Cohort, ...] = (
    Cohort(id="binge", name="Binge Listeners",
           weights={"urgency": 0.6, "open_obligations": 0.3, "fairness": 0.1}),
    Cohort(id="lore", name="Lore Hardcores",
           weights={"fairness": 0.7, "open_obligations": 0.2, "urgency": 0.1}),
    Cohort(id="character", name="Character Fans",
           weights={"emotional_payoff": 0.7, "urgency": 0.2, "fairness": 0.1}),
    Cohort(id="commuter", name="Casual Commuters",
           weights={"clarity": 0.6, "urgency": 0.3, "fairness": 0.1}),
    Cohort(id="aggregate", name="Aggregate Health",
           weights={"consistency": 0.4, "fairness": 0.3, "urgency": 0.15, "emotional_payoff": 0.15}),
)
```

- [ ] **Step 3: Run the existing test suite**

Run: `.venv/bin/python -m pytest tests/test_cohorts.py -v`
Expected: PASS unchanged — the test asserts structural properties (`len == 5`, weights differ, `backend == "local-structural"`) not specific ids/names.

- [ ] **Step 4: Write the failing test for the dormant Databricks path**

Add to `tests/test_cohorts.py`:

```python
from app.cohorts import databricks_cohort_reaction


def test_databricks_cohort_reaction_labels_its_backend():
    calls = []

    def fake_query(sql: str, params: dict) -> list[tuple]:
        calls.append((sql, params))
        return [(0.71,)]

    reaction = databricks_cohort_reaction(COHORTS[0], episode=12, series_id="s1", query=fake_query)
    assert reaction.backend == "databricks-ai_query"
    assert reaction.engagement == 0.71
    assert len(calls) == 1
```

- [ ] **Step 5: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_cohorts.py::test_databricks_cohort_reaction_labels_its_backend -v`
Expected: FAIL with `ImportError: cannot import name 'databricks_cohort_reaction'`

- [ ] **Step 6: Implement**

Add to `app/cohorts.py`, after `structural_reaction`:

```python
from typing import Callable, Protocol


class _CohortQuery(Protocol):
    def __call__(self, sql: str, params: dict) -> list[tuple]: ...


def databricks_cohort_reaction(cohort: Cohort, episode: int, series_id: str, query: _CohortQuery) -> CohortReaction:
    """Governed on-platform cohort scoring, shaped like DatabricksExtractor's ai_query call.

    Not wired to any API route: this environment has no Databricks workspace
    to run it against. It exists so "real path for the 5-cohort simulator"
    is not just an unfulfilled spec line -- the deterministic
    `structural_reaction` above is the only path actually served by
    /api/cohorts today, and stays so until this is configured and wired the
    same opt-in way Task 2/3/4 wired OpenAI.
    """
    sql = (
        "SELECT ai_query('cohort-reaction-model', named_struct("
        "'cohort_id', :cohort_id, 'episode', :episode, 'series_id', :series_id))"
    )
    rows = query(sql, {"cohort_id": cohort.id, "episode": episode, "series_id": series_id})
    engagement = float(rows[0][0]) if rows else 0.0
    vote = "continue" if engagement >= 0.67 else "hesitate" if engagement >= 0.42 else "stop"
    return CohortReaction(
        cohort_id=cohort.id,
        episode=episode,
        engagement=round(engagement, 6),
        vote=vote,
        reaction=f"{cohort.name} responds via the governed Databricks cohort query with {vote}.",
        backend="databricks-ai_query",
    )
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_cohorts.py -v`
Expected: all PASS

- [ ] **Step 8: Run full suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: all PASS

- [ ] **Step 9: Commit**

```bash
git add app/cohorts.py tests/test_cohorts.py
git commit -m "$(cat <<'EOF'
feat: rename cohorts to spec names, add dormant Databricks cohort path

Cohorts were named Binge Listener/Mystery Purist/Romance Listener/
Skeptic/Late-Night Listener; renamed to the spec's Binge Listeners/
Lore Hardcores/Character Fans/Casual Commuters/Aggregate Health.
Added databricks_cohort_reaction, shaped like DatabricksExtractor's
ai_query call -- not wired to any route since no Databricks workspace
is available in this environment; /api/cohorts keeps using the
deterministic structural_reaction default.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Document the sklearn-vs-LightGBM deviation

**Files:**
- Modify: `app/predictor.py:1-13` (module docstring only)

**Interfaces:** none — documentation only, no behavior change.

- [ ] **Step 1: Edit the docstring**

Modify `app/predictor.py`, in the module docstring, after the existing paragraph ending "...they are not calibrated to real audiences. Say so wherever a number is shown.", add:

```python
"""Structural features -> predicted next-episode continuation.

The model consumes only the graph-derived vector. It never sees prose, and that
is deliberate: a rewrite cannot raise this score by sounding better, only by
changing structure -- closing an obligation, raising urgency, shortening the gap
to a payoff. Without that property the generator would be grading its own work.

Fit to a synthetic corpus with a documented generative process (see
``app/training_corpus.py``), not to observed reader behaviour and not to platform
telemetry. Nothing in this repository ingests real retention labels yet, so these
predictions demonstrate that the pipeline runs end to end -- they are not
calibrated to real audiences. Say so wherever a number is shown.

Deliberate deviation from an early spec draft that named LightGBM: this uses
scikit-learn's GradientBoostingRegressor instead. It is already integrated with
this module's MLflow logging and empirical-quantile calibration, is well tested,
and produces the same class of gradient-boosted-tree model the spec's choice
would have -- swapping libraries here would be pure churn with no behavioural
difference, so it was not done.
"""
```

- [ ] **Step 2: Run the predictor test suite to confirm nothing broke**

Run: `.venv/bin/python -m pytest tests/test_predictor.py -v`
Expected: all PASS (docstring-only change)

- [ ] **Step 3: Commit**

```bash
git add app/predictor.py
git commit -m "$(cat <<'EOF'
docs: note the deliberate sklearn-vs-LightGBM deviation from spec

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Surgical Node Repair — generate the replacement text via OpenAI

**Files:**
- Modify: `app/llm_agents.py`
- Modify: `app/main.py` (`/api/repair` route, `RepairRequest` model)
- Test: `tests/test_llm_agents.py`, new route test in `tests/test_api_v2.py`

**Interfaces:**
- Consumes: `app.variants.RepairEngine` (existing, unchanged), `app.llm_config.openai_config` (Task 0).
- Produces: `app.llm_agents.propose_repair_text(series, target_entry_id, node_id, *, endpoint, token, model, cache_path=None, transport=None) -> tuple[str, str]` returning `(replacement_text, backend)`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_llm_agents.py`:

```python
from app.llm_agents import propose_repair_text
from app.ledger import LedgerResolver


def test_propose_repair_text_targets_a_broken_entry_node():
    series = _series()
    resolved = [item for item in LedgerResolver().resolve_series(series) if item.state == "broken"]
    if not resolved:
        import pytest
        pytest.skip("fixture series has no broken entry to repair -- adjust fixture reference before relying on this")
    target = resolved[0]
    node = next(n for n in series.nodes if n.episode == max(target.entry.episodes))

    def fake_transport(*, endpoint, token, model, prompt):
        assert node.summary in prompt
        return "  A corrected version of the scene.  "

    text, backend = propose_repair_text(
        series, target.entry.id, node.id,
        endpoint="https://api.openai.com/v1/chat/completions", token="sk-test", model="gpt-4o-mini",
        transport=fake_transport,
    )
    assert text == "A corrected version of the scene."
    assert backend == "openai"


def test_propose_repair_text_rejects_unknown_entry():
    import pytest
    series = _series()
    with pytest.raises(ValueError, match="unknown ledger entry"):
        propose_repair_text(
            series, "no-such-entry", "n-1",
            endpoint="https://api.openai.com/v1/chat/completions", token="sk-test", model="gpt-4o-mini",
            transport=lambda **kwargs: "x",
        )
```

Before trusting the first test's `resolved` lookup, check whether `tests/test_variants.py::_series` actually has a `broken` entry (the fixture used throughout `test_variants.py`'s `RepairEngine` tests must have one, since those tests exercise `repair()` which requires `state == "broken"` — read `tests/test_variants.py` to find the exact `target_entry_id`/`node_id` it already uses and reuse those same values instead of re-deriving them, for consistency with the rest of the suite).

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_llm_agents.py -k propose_repair_text -v`
Expected: FAIL with `ImportError: cannot import name 'propose_repair_text'`

- [ ] **Step 3: Implement**

Add to `app/llm_agents.py`, after `LLMPersonaHandler`:

```python
_REPAIR_PROMPT = (
    "Rewrite the following scene summary so it no longer contradicts the "
    "stated obligation, changing as little as possible. Respond with the "
    "replacement summary text only -- no prose, no JSON, no quotes, no "
    "markdown fences.\n"
    "Obligation it must stop contradicting: {description}\n"
    "Original scene summary: {summary}"
)


def propose_repair_text(
    series: Series,
    target_entry_id: str,
    node_id: str,
    *,
    endpoint: str,
    token: str,
    model: str,
    cache_path: str | Path | None = None,
    transport: Transport | None = None,
) -> tuple[str, str]:
    """Generate replacement text for one corrupt node via a real model call.

    Returns (replacement_text, backend). Callers still go through
    RepairEngine.repair for the actual graph mutation, node targeting, and
    "only a broken entry may be repaired" rule -- this function only produces
    the text that mutation needs.
    """
    entry = next((item for item in series.entries if item.id == target_entry_id), None)
    if entry is None:
        raise ValueError(f"unknown ledger entry: {target_entry_id}")
    node = next((item for item in series.nodes if item.id == node_id), None)
    if node is None:
        raise ValueError(f"unknown repair node: {node_id}")

    prompt = _REPAIR_PROMPT.format(description=entry.description, summary=node.summary)
    transport_fn = transport or _http_transport
    backend = backend_for(endpoint)

    cache_file = Path(cache_path) if cache_path else None
    cache: dict[str, str] = {}
    if cache_file and cache_file.exists():
        cache = json.loads(cache_file.read_text(encoding="utf-8"))

    key = cache_key(model, prompt)
    if key in cache:
        raw = cache[key]
    else:
        raw = transport_fn(endpoint=endpoint, token=token, model=model, prompt=prompt)
        cache[key] = raw
        if cache_file is not None:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")

    return raw.strip(), backend
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_llm_agents.py -v`
Expected: all PASS

- [ ] **Step 5: Wire into `/api/repair`**

Modify `app/main.py`. Change `RepairRequest`:

```python
class RepairRequest(BaseModel):
    target_entry_id: str
    node_id: str
    replacement_summary: str | None = None
```

Add to the `app.llm_agents` import line already added in Task 4 (extend it):

```python
from app.llm_agents import LLMPersonaHandler, propose_repair_text
```

Replace the `/api/repair` route:

```python
    @app.post("/api/repair")
    def repair(payload: RepairRequest) -> dict:
        current = _series()
        replacement_summary = payload.replacement_summary
        repair_backend = "caller-supplied"
        if replacement_summary is None:
            config = openai_config()
            if config is None:
                raise HTTPException(
                    status_code=422,
                    detail="replacement_summary was not supplied and OPENAI_API_KEY is not configured to generate one",
                )
            try:
                replacement_summary, repair_backend = propose_repair_text(
                    current, payload.target_entry_id, payload.node_id,
                    endpoint=config.endpoint, token=config.token, model=config.model,
                    cache_path="data/extraction_cache/repair_openai.json",
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        try:
            variant = RepairEngine().repair(current, payload.target_entry_id, payload.node_id, replacement_summary)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        result = variant.model_dump()
        result["repair_backend"] = repair_backend
        result["score"] = _predictor().score_variant(current, variant.series, current.total_episodes).model_dump()
        return result
```

- [ ] **Step 6: Write a route-level test**

Add to `tests/test_api_v2.py`:

```python
def test_repair_route_requires_openai_key_when_text_omitted(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post("/api/repair", json={"target_entry_id": "no-such-entry", "node_id": "no-such-node"})
    assert response.status_code == 422
    assert "OPENAI_API_KEY" in response.json()["detail"]
```

(Match the file's existing fixture style — if there's no `client`/`monkeypatch`-taking fixture already, build the client inline as done elsewhere in this plan.)

- [ ] **Step 7: Run full suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: all PASS

- [ ] **Step 8: Commit**

```bash
git add app/llm_agents.py app/main.py tests/test_llm_agents.py tests/test_api_v2.py
git commit -m "$(cat <<'EOF'
feat: generate surgical repair text via OpenAI when not caller-supplied

RepairEngine already targeted one node, required a broken (not
suspended) entry, and preserved the rest of the graph -- the only
missing piece was who writes the replacement text. /api/repair now
calls propose_repair_text (real OpenAI call, cached) when
replacement_summary is omitted, and 422s naming the missing config
instead of fabricating a template when OPENAI_API_KEY isn't set.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Pre-Publish retention delta

**Files:**
- Modify: `app/prepublish.py`
- Modify: `app/main.py` (`/api/prepublish` route)
- Test: `tests/test_prepublish.py`

**Interfaces:**
- Consumes: `app.predictor.ContinuationPredictor` / `app.predictor.Prediction` (existing), `app.features.FeatureExtractor` (existing).
- Produces: `PrePublishReport.retention_delta: float | None`, `PrePublishReport.prediction: Prediction | None`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_prepublish.py`:

```python
def test_pre_publish_check_reports_a_retention_delta():
    client = TestClient(create_app())
    candidate = {
        "episode": 221,
        "text": "Asha promises she will return to the ferry, but the old locket is silver.",
    }
    response = client.post("/api/prepublish", json=candidate)
    assert response.status_code == 200
    payload = response.json()
    assert payload["retention_delta"] is not None
    assert payload["prediction"] is not None
    assert "value" in payload["prediction"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_prepublish.py -v`
Expected: FAIL — `KeyError`/`None` where a value is expected (fields don't exist yet).

- [ ] **Step 3: Extend `PrePublishReport`**

Modify `app/prepublish.py`, add the import and fields:

```python
from app.predictor import Prediction


class PrePublishReport(BaseModel):
    series_id: str
    source: str = "file"
    candidate_episode: int
    complete: bool
    extraction_rejected: int
    findings: list[ResolvedEntry]
    retention_delta: float | None = None
    prediction: Prediction | None = None
```

`PrePublishChecker.check` stays predictor-agnostic (unchanged) — the predictor call happens in `main.py`, matching where every other prediction call in this codebase already lives (`_predictor()` is only ever called from route handlers).

- [ ] **Step 4: Wire the predictor call into the route**

Modify `app/main.py`, replace the `/api/prepublish` route:

```python
    @app.post("/api/prepublish", response_model=PrePublishReport)
    def prepublish(payload: PrePublishRequest) -> PrePublishReport:
        current = _series()
        if payload.episode <= current.total_episodes:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"candidate episode must follow the published series; "
                    f"received {payload.episode} after {current.total_episodes}"
                ),
            )
        report = PrePublishChecker().check(current, payload)
        if report.complete:
            predictor = _predictor()
            before = predictor.predict(FeatureExtractor().extract(current, current.total_episodes))
            candidate_series = current.model_copy(update={"total_episodes": payload.episode})
            after = predictor.predict(FeatureExtractor().extract(candidate_series, payload.episode))
            report = report.model_copy(update={"retention_delta": after.value - before.value, "prediction": after})
        return report.model_copy(update={"source": _store().backend})
```

Note: `FeatureExtractor().extract(candidate_series, payload.episode)` needs `candidate_series` to actually contain nodes/entries for `payload.episode` — `current.model_copy(update={"total_episodes": payload.episode})` alone does NOT add the candidate's extracted graph content. Use `PrePublishChecker`'s own candidate series instead: expose it from the checker rather than recomputing. Change `PrePublishChecker.check` to return the candidate series alongside the report (modify `app/prepublish.py` further):

```python
class PrePublishChecker:
    """Run a candidate through extraction and ledger resolution without mutation."""

    def __init__(self, extractor: HeuristicExtractor | None = None) -> None:
        self._extractor = extractor or HeuristicExtractor()

    def check(self, series: Series, request: PrePublishRequest) -> tuple[PrePublishReport, Series]:
        rows = [
            {"episode": excerpt.episode, "synopsis": excerpt.text}
            for excerpt in sorted(series.excerpts, key=lambda item: item.episode)
        ]
        rows.append({"episode": request.episode, "synopsis": request.text})
        extraction = self._extractor.extract(rows)
        candidate_series = series.model_copy(
            deep=True,
            update={
                "total_episodes": request.episode,
                "ongoing": True,
                "nodes": extraction.nodes,
                "entries": extraction.entries,
                "payoffs": extraction.payoffs,
                "excerpts": extraction.excerpts,
            },
        )
        resolved = LedgerResolver().resolve_series(candidate_series, as_of=request.episode)
        findings = [
            item
            for item in resolved
            if item.entry.latest_episode == request.episode and item.state != "paid"
        ]
        report = PrePublishReport(
            series_id=series.id,
            candidate_episode=request.episode,
            complete=extraction.rejected == 0,
            extraction_rejected=extraction.rejected,
            findings=findings,
        )
        return report, candidate_series
```

This changes `check`'s return type from `PrePublishReport` to `tuple[PrePublishReport, Series]` — a breaking change to its call sites. Update the route in `app/main.py` accordingly:

```python
    @app.post("/api/prepublish", response_model=PrePublishReport)
    def prepublish(payload: PrePublishRequest) -> PrePublishReport:
        current = _series()
        if payload.episode <= current.total_episodes:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"candidate episode must follow the published series; "
                    f"received {payload.episode} after {current.total_episodes}"
                ),
            )
        report, candidate_series = PrePublishChecker().check(current, payload)
        if report.complete:
            predictor = _predictor()
            before = predictor.predict(FeatureExtractor().extract(current, current.total_episodes))
            after = predictor.predict(FeatureExtractor().extract(candidate_series, payload.episode))
            report = report.model_copy(update={"retention_delta": after.value - before.value, "prediction": after})
        return report.model_copy(update={"source": _store().backend})
```

- [ ] **Step 5: Check for other callers of `PrePublishChecker.check`**

Run:

```bash
grep -rn "PrePublishChecker()" /home/lathiss/Projects/Zero-to-One_AI_Hackathon/app /home/lathiss/Projects/Zero-to-One_AI_Hackathon/tests
```

Update any other call site found to unpack `report, candidate_series = PrePublishChecker().check(...)` instead of `report = PrePublishChecker().check(...)`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_prepublish.py -v`
Expected: all PASS

- [ ] **Step 7: Run full suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: all PASS

- [ ] **Step 8: Commit**

```bash
git add app/prepublish.py app/main.py tests/test_prepublish.py
git commit -m "$(cat <<'EOF'
feat: add retention delta to the Pre-Publish Check surface

PrePublishChecker.check now returns the candidate series alongside
the report so /api/prepublish can predict before/after and attach
retention_delta and prediction -- the spec's "live retention impact
deltas" was previously entirely absent from this surface.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: Narrative Debt Index (NDI) on the Showrunner Debt Board

**Files:**
- Modify: `app/surfaces.py`
- Test: `tests/test_surfaces.py`

**Interfaces:**
- Produces: `DebtBoard.narrative_debt_index: float`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_surfaces.py`:

```python
def test_debt_board_reports_a_named_narrative_debt_index():
    from app.surfaces import DebtBoardQuery
    from tests.test_variants import _series

    board = DebtBoardQuery().aggregate([(_series(), {})])
    if board.items:
        expected = sum(item.risk for item in board.items) / len(board.items)
        assert board.narrative_debt_index == expected
    else:
        assert board.narrative_debt_index == 0.0


def test_debt_board_index_is_zero_for_an_empty_board():
    from app.surfaces import DebtBoardQuery

    board = DebtBoardQuery().aggregate([], series_ids=set())
    assert board.narrative_debt_index == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_surfaces.py -k narrative_debt_index -v`
Expected: FAIL — `AttributeError: 'DebtBoard' object has no attribute 'narrative_debt_index'`

- [ ] **Step 3: Implement**

Modify `app/surfaces.py`. Update `DebtBoard`:

```python
class DebtBoard(BaseModel):
    items: list[DebtBoardItem] = Field(default_factory=list)
    total_open: int
    narrative_debt_index: float = 0.0
    filters: dict[str, str | int | None] = Field(default_factory=dict)
```

Update `DebtBoardQuery.aggregate`'s return statement (end of the method):

```python
        items.sort(key=lambda item: (-item.risk, item.series_id, item.entry.entry.id))
        ndi = sum(item.risk for item in items) / len(items) if items else 0.0
        return DebtBoard(
            items=items,
            total_open=len(items),
            narrative_debt_index=ndi,
            filters={"writer_id": writer_id, "state": state, "genre": genre, "urgency": urgency},
        )
```

Add a one-line docstring note above `DebtBoard` clarifying the name:

```python
class DebtBoard(BaseModel):
    """`narrative_debt_index` is the mean per-item `risk` across all open
    entries on the board (0.0 when empty) -- the spec names this NDI without
    defining a formula; this is the explicit, stated one."""

    items: list[DebtBoardItem] = Field(default_factory=list)
    total_open: int
    narrative_debt_index: float = 0.0
    filters: dict[str, str | int | None] = Field(default_factory=dict)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_surfaces.py -v`
Expected: all PASS

- [ ] **Step 5: Run full suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add app/surfaces.py tests/test_surfaces.py
git commit -m "$(cat <<'EOF'
feat: name and compute the Narrative Debt Index on the Debt Board

The spec names "NDI" without a formula; DebtBoard.narrative_debt_index
is now the explicit, documented mean per-item risk (0.0 when empty)
instead of an implicit synonym nobody could point to.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: Localization graph-parity check

**Files:**
- Modify: `app/surfaces.py`
- Test: `tests/test_surfaces.py`

**Interfaces:**
- Consumes: `app.heuristic_extractor.HeuristicExtractor` (existing).
- Produces: an additional `LocalizationFinding(dimension="graph_parity", ...)` emitted by `LocalizationChecker.check` when warranted.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_surfaces.py`:

```python
def test_localization_check_flags_entity_count_mismatch_via_graph_parity():
    from app.surfaces import LocalizationChecker, LocalizationEpisode
    from tests.test_variants import _series

    series = _series()
    source_excerpt = next(e for e in series.excerpts if e.episode == 1)
    translated = LocalizationEpisode(episode=1, language="es", text="Un capitulo sin ningun nombre reconocible.")

    report = LocalizationChecker().check(source_excerpt, translated, series)
    dims = {finding.dimension for finding in report.findings}
    assert "graph_parity" in dims
```

Before writing this test, confirm episode 1 of `tests/test_variants.py::_series` actually has at least one named entity in its node (`series.nodes` with `episode == 1` and non-empty `entities`) — if not, pick whichever episode does, matching the pattern the existing `test_the-translation-does-not-preserve-a-named-entity` test in `tests/test_surfaces.py` already uses (read that existing test first for the exact fixture episode/text it relies on).

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_surfaces.py -k graph_parity -v`
Expected: FAIL — no `graph_parity` dimension is ever emitted yet.

- [ ] **Step 3: Implement**

Modify `app/surfaces.py`. Add the import:

```python
from app.heuristic_extractor import HeuristicExtractor
```

Modify `LocalizationChecker.check`, adding one more finding before the `return` statement:

```python
class LocalizationChecker:
    def check(self, source_excerpt: Excerpt, translated: LocalizationEpisode, series: Series) -> LocalizationReport:
        findings: list[LocalizationFinding] = []
        translated_id = f"translation-{translated.language}-{translated.episode}"
        citation_ids = [source_excerpt.id, translated_id]
        source_words = set(re.findall(r"[A-Za-z]+", source_excerpt.text.lower()))
        translated_words = set(re.findall(r"[A-Za-z]+", translated.text.lower()))
        source_colours = source_words & _COLOURS
        translated_colours = translated_words & _COLOURS
        if source_colours != translated_colours:
            findings.append(LocalizationFinding(dimension="colour", severity="warning", message=f"source colours {sorted(source_colours)} differ from translation {sorted(translated_colours)}", citation_ids=citation_ids))
        source_numbers = _NUMBER.findall(source_excerpt.text)
        if source_numbers != _NUMBER.findall(translated.text):
            findings.append(LocalizationFinding(dimension="numbers", severity="error", message="numeric facts differ between source and translation", citation_ids=citation_ids))
        source_temporal = source_words & _TEMPORAL
        if source_temporal and not source_temporal & translated_words:
            findings.append(LocalizationFinding(dimension="temporal_marker", severity="warning", message="the translation drops a source temporal marker", citation_ids=citation_ids))
        names = {node_entity.lower() for node in series.nodes if node.episode == source_excerpt.episode for node_entity in node.entities}
        if names and not names & translated_words:
            findings.append(LocalizationFinding(dimension="entity_name", severity="error", message="the translation does not preserve a named entity from the source episode", citation_ids=citation_ids))

        # Graph-derived parity check: extract a one-off mini-graph from the
        # translated text and compare its entity count against the source
        # node's. Still heuristic (no cross-language embeddings -- out of
        # scope), but it is graph-derived rather than pure word-overlap.
        source_entity_count = len(names)
        translated_extraction = HeuristicExtractor().extract(
            [{"episode": translated.episode, "synopsis": translated.text}]
        )
        translated_entity_count = len(
            {entity for node in translated_extraction.nodes for entity in node.entities}
        )
        if source_entity_count and translated_entity_count != source_entity_count:
            findings.append(
                LocalizationFinding(
                    dimension="graph_parity",
                    severity="warning",
                    message=(
                        f"translated episode's extracted entity count ({translated_entity_count}) "
                        f"does not match the source episode's ({source_entity_count})"
                    ),
                    citation_ids=citation_ids,
                )
            )

        source_findings = [
            item for item in LedgerResolver().resolve_series(series, as_of=source_excerpt.episode)
            if source_excerpt.episode in item.entry.episodes and item.state != "paid"
        ]
        return LocalizationReport(series_id=series.id, episode=translated.episode, language=translated.language, source_version=series.source_version, translated_excerpt_id=translated_id, findings=findings, source_story_findings=source_findings)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_surfaces.py -v`
Expected: all PASS. If the new test's fixture assumption from Step 1 doesn't hold (e.g. `source_entity_count` ends up 0 because episode 1 has no named entities), adjust the test's `translated` text or episode number to one where the source node does carry entities, then re-run.

- [ ] **Step 5: Run full suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add app/surfaces.py tests/test_surfaces.py
git commit -m "$(cat <<'EOF'
feat: add graph-derived parity check to Localization Check

LocalizationChecker previously only diffed colour/number/temporal/
entity words between source and translated text. Adds a graph_parity
finding comparing entity counts from a one-off HeuristicExtractor pass
over the translated text against the source node -- still heuristic,
not full cross-language semantic edge alignment, but graph-derived
rather than pure word-overlap.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Final verification

- [ ] Run the complete suite once more: `.venv/bin/python -m pytest tests/ -q` — expect all green.
- [ ] Run `grep -rn "OPENAI_API_KEY" app/ | grep -v llm_config.py` — expect zero results outside `app/llm_config.py` (every other module goes through `openai_config()`).
