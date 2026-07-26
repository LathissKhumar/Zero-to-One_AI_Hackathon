"""Local, deterministic implementation of CanonPulse's two-speed ingest seam.

The production adapter can persist the same lifecycle in Delta.  This module
keeps the public contract useful offline: a synopsis graph is available as
soon as submission validation completes and a deep run is promoted atomically
only after its complete graph has been built.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.heuristic_extractor import HeuristicExtractor
from app.narrative_models import Series


class SubmissionEpisode(BaseModel):
    episode: int = Field(ge=1)
    synopsis: str = Field(min_length=1)
    body: str | None = None
    writer_id: str = "unknown"
    language: str = "en"


class Submission(BaseModel):
    series_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    genre: str = Field(min_length=1)
    episodes: list[SubmissionEpisode] = Field(min_length=1, max_length=300)
    ongoing: bool = True

    @model_validator(mode="after")
    def _episodes_are_ordered_and_unique(self) -> "Submission":
        numbers = [episode.episode for episode in self.episodes]
        if numbers != sorted(numbers) or len(numbers) != len(set(numbers)):
            raise ValueError("episodes must be unique and sorted")
        return self


class IngestJob(BaseModel):
    job_id: str
    series_id: str
    status: Literal["received", "validated", "synopsis_ready", "complete", "failed"]
    deep_status: Literal["pending", "running", "complete", "failed"] = "pending"
    accepted: int = 0
    rejected: int = 0
    retried: int = 0
    series: Series
    error: str | None = None


def _series_from_result(submission: Submission, result, *, source_version: str) -> Series:
    writer_map = {str(item.episode): item.writer_id for item in submission.episodes}
    language_map = {str(item.episode): item.language for item in submission.episodes}
    return Series(
        id=submission.series_id,
        title=submission.title,
        genre=submission.genre,
        total_episodes=max(item.episode for item in submission.episodes),
        ongoing=submission.ongoing,
        nodes=result.nodes,
        entries=result.entries,
        payoffs=result.payoffs,
        excerpts=result.excerpts,
        source_version=source_version,
        episode_writers=writer_map,
        episode_languages=language_map,
    )


class IngestService:
    """Idempotent in-memory job store used by local mode and API tests."""

    def __init__(self) -> None:
        self._jobs: dict[str, IngestJob] = {}
        self._submissions: dict[str, Submission] = {}

    @staticmethod
    def _job_id(submission: Submission) -> str:
        encoded = json.dumps(submission.model_dump(), sort_keys=True).encode()
        return hashlib.sha256(encoded).hexdigest()[:16]

    @staticmethod
    def _source_version(submission: Submission, deep: bool) -> str:
        payload = {"deep": deep, **submission.model_dump()}
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    @staticmethod
    def _rows(submission: Submission, *, deep: bool) -> list[dict]:
        return [
            {
                "episode": item.episode,
                "synopsis": item.synopsis,
                "body": item.body if deep else None,
            }
            for item in submission.episodes
        ]

    def submit(self, submission: Submission) -> IngestJob:
        job_id = self._job_id(submission)
        if job_id in self._jobs:
            return self._jobs[job_id].model_copy(deep=True)
        self._submissions[job_id] = submission.model_copy(deep=True)
        result = SynopsisExtractor().extract(self._rows(submission, deep=False))
        job = IngestJob(
            job_id=job_id,
            series_id=submission.series_id,
            status="synopsis_ready",
            accepted=len(result.nodes),
            rejected=result.rejected,
            series=_series_from_result(
                submission, result, source_version=self._source_version(submission, False)
            ),
        )
        self._jobs[job_id] = job
        return job.model_copy(deep=True)

    def get(self, job_id: str) -> IngestJob:
        try:
            return self._jobs[job_id].model_copy(deep=True)
        except KeyError as exc:
            raise KeyError(f"unknown ingest job: {job_id}") from exc

    def run_deep(self, job_id: str) -> IngestJob:
        job = self._jobs[job_id]
        if job.deep_status == "complete":
            return job.model_copy(deep=True)
        submission = self._submissions[job_id]
        job.deep_status = "running"
        result = HeuristicExtractor().extract(self._rows(submission, deep=True))
        promoted = _series_from_result(
            submission, result, source_version=self._source_version(submission, True)
        )
        job.series = promoted
        job.status = "complete"
        job.deep_status = "complete"
        job.accepted = len(result.nodes)
        job.rejected = result.rejected
        self._jobs[job_id] = job
        return job.model_copy(deep=True)


class SynopsisExtractor:
    """Fast bounded adapter used before full episode bodies are available."""

    backend = "synopsis-local"

    def extract(self, episodes: list[dict]):
        result = HeuristicExtractor().extract(
            [{"episode": row["episode"], "synopsis": row.get("synopsis", "")} for row in episodes]
        )
        for entry in result.entries:
            entry.confidence = 0.4
        result.backend = self.backend
        return result
