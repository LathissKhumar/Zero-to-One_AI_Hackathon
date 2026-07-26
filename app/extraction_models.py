"""Provenance contracts for graph extraction outputs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ExtractionContext(BaseModel):
    series_id: str = Field(min_length=1)
    version_id: str = Field(min_length=1)
    source_hash: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)


class SourceCitation(BaseModel):
    series_id: str = Field(min_length=1)
    version_id: str = Field(min_length=1)
    episode_number: int = Field(ge=1)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)
    quote_hash: str = Field(min_length=1)
    source_path: str | None = None
    source_pages: list[int] = Field(default_factory=list)
    source_element_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_span_and_version(self) -> "SourceCitation":
        if self.end_offset <= self.start_offset:
            raise ValueError("citation end_offset must be greater than start_offset")
        if not self.quote_hash.startswith(f"{self.version_id}:"):
            raise ValueError("citation quote_hash version_id does not match version_id")
        return self

    @classmethod
    def from_text(
        cls, *, series_id: str, version_id: str, episode_number: int, text: str, start_offset: int = 0, end_offset: int | None = None,
        source_path: str | None = None, source_pages: list[int] | None = None, source_element_ids: list[int] | None = None,
    ) -> "SourceCitation":
        import hashlib

        end = len(text) if end_offset is None else end_offset
        quote_hash = hashlib.sha256(f"{version_id}:{text[start_offset:end]}".encode()).hexdigest()
        return cls(
            series_id=series_id,
            version_id=version_id,
            episode_number=episode_number,
            start_offset=start_offset,
            end_offset=end,
            quote_hash=f"{version_id}:{quote_hash}",
            source_path=source_path,
            source_pages=source_pages or [],
            source_element_ids=source_element_ids or [],
        )


class ExtractionFailure(BaseModel):
    code: Literal["timeout", "rate_limit", "service_unavailable", "schema", "citation", "input"]
    message: str = Field(min_length=1)
    retryable: bool
    episode_number: int | None = Field(default=None, ge=1)


class ExtractionRunMetadata(BaseModel):
    run_id: str = Field(min_length=1)
    source_hash: str = Field(min_length=1)
    version_id: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    started_at: datetime
    finished_at: datetime
    latency_ms: float = Field(ge=0)
    attempt: int = Field(ge=1)

    @model_validator(mode="after")
    def finished_after_started(self) -> "ExtractionRunMetadata":
        if self.finished_at < self.started_at:
            raise ValueError("finished_at must not precede started_at")
        return self


def metadata_for(context: ExtractionContext, *, run_id: str, started_at: datetime, latency_ms: float, attempt: int = 1) -> ExtractionRunMetadata:
    return ExtractionRunMetadata(
        run_id=run_id,
        source_hash=context.source_hash,
        version_id=context.version_id,
        model_name=context.model_name,
        prompt_version=context.prompt_version,
        started_at=started_at,
        finished_at=datetime.now(timezone.utc),
        latency_ms=latency_ms,
        attempt=attempt,
    )
