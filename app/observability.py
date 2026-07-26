"""Correlated, redaction-safe runtime events."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel, Field, model_validator


class RunContext(BaseModel):
    request_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    series_id: str = Field(min_length=1)
    version_id: str = Field(min_length=1)
    source_version: str = Field(min_length=1)
    model_version: str = Field(min_length=1)


class OperationalEvent(BaseModel):
    event_name: Literal["request", "ingestion", "extraction", "prediction", "retrieval", "cohort", "evaluation"]
    context: RunContext
    started_at: datetime
    finished_at: datetime
    latency_ms: float = Field(ge=0)
    status: Literal["ok", "failed", "rejected", "timeout"]
    cost_usd: float = Field(ge=0)
    metadata: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_context(self) -> "OperationalEvent":
        if not self.context.request_id:
            raise ValueError("request_id is required")
        if self.finished_at < self.started_at:
            raise ValueError("finished_at must not precede started_at")
        return self


class EventSink(Protocol):
    def emit(self, event: OperationalEvent) -> None: ...


class InMemoryEventSink:
    def __init__(self) -> None:
        self.events: list[OperationalEvent] = []

    def emit(self, event: OperationalEvent) -> None:
        self.events.append(event.model_copy(deep=True))


EVENT_SINK = InMemoryEventSink()
