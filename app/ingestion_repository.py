"""Persistence boundary for immutable submission versions and work items."""

from __future__ import annotations

import hashlib
from typing import Protocol

from app.ingestion_models import EpisodeWorkItem, IngestionJob, SubmissionInput


class SubmissionRepository(Protocol):
    def create_submission(self, submission: SubmissionInput, source_hash: str) -> IngestionJob: ...

    def list_work_items(self, job_id: str, stage: str) -> list[EpisodeWorkItem]: ...

    def update_work_item(self, job_id: str, episode_number: int, stage: str, status: str, error: str | None = None) -> None: ...

    def promote_fast_ledger(self, job_id: str) -> None: ...


class InMemorySubmissionRepository:
    """Deterministic adapter for local mode and unit tests."""

    def __init__(self) -> None:
        self.jobs: dict[str, IngestionJob] = {}
        self.work_items: dict[tuple[str, int, str], EpisodeWorkItem] = {}
        self._source_jobs: dict[tuple[str, str], str] = {}

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
