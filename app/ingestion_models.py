"""Validated contracts shared by upload, persistence, and ingestion workers."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Iterable, Literal

from pydantic import BaseModel, Field, model_validator


class EpisodeInput(BaseModel):
    episode_number: int = Field(ge=1)
    text: str = Field(min_length=1)
    synopsis: str | None = None
    writer_id: str = "unknown"
    language: str = "en"
    source_path: str | None = None
    source_pages: list[int] = Field(default_factory=list)
    source_element_ids: list[int] = Field(default_factory=list)


class SubmissionInput(BaseModel):
    series_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    genre: str = Field(min_length=1)
    episodes: list[EpisodeInput] = Field(min_length=1, max_length=300)
    ongoing: bool = True

    @model_validator(mode="after")
    def unique_episode_numbers(self) -> "SubmissionInput":
        numbers = [episode.episode_number for episode in self.episodes]
        if len(numbers) != len(set(numbers)):
            raise ValueError("duplicate episode_number")
        return self


class EpisodeWorkItem(BaseModel):
    job_id: str
    episode_number: int
    stage: Literal["fast", "deep"]
    status: Literal["queued", "running", "complete", "failed", "cancelled", "stale"] = "queued"
    attempt_count: int = 0
    error: str | None = None


class IngestionJob(BaseModel):
    job_id: str
    series_id: str
    source_hash: str
    status: Literal["queued", "fast_running", "fast_ready", "deep_running", "complete", "partial", "cancelled"] = "queued"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_episodes: int = 0
    failed_episodes: list[int] = Field(default_factory=list)
    reprocessed_episodes: list[int] = Field(default_factory=list)


class IngestionStatus(BaseModel):
    job_id: str
    status: IngestionJob.model_fields["status"].annotation
    completed_episodes: int = 0
    failed_episodes: list[int] = Field(default_factory=list)
    reprocessed_episodes: list[int] = Field(default_factory=list)


def _normalize(submission: SubmissionInput) -> SubmissionInput:
    return submission.model_copy(
        update={"episodes": sorted(submission.episodes, key=lambda episode: episode.episode_number)}
    )


def parse_submission_json(raw: bytes) -> SubmissionInput:
    return _normalize(SubmissionInput.model_validate_json(raw))


def parse_submission_ndjson(lines: Iterable[bytes]) -> SubmissionInput:
    episodes = [EpisodeInput.model_validate_json(line) for line in lines if line.strip()]
    numbers = [episode.episode_number for episode in episodes]
    if len(numbers) != len(set(numbers)):
        raise ValueError("duplicate episode_number")
    return SubmissionInput(
        series_id="uploaded",
        title="Uploaded series",
        genre="serialized fiction",
        episodes=sorted(episodes, key=lambda episode: episode.episode_number),
    )


def submission_source_hash(submission: SubmissionInput) -> str:
    encoded = json.dumps(submission.model_dump(mode="json"), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()
