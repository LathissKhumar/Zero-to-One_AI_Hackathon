"""Contracts for governed retrieval and synthetic cohort reactions."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from app.extraction_models import SourceCitation


class CohortRequest(BaseModel):
    series_id: str = Field(min_length=1)
    version_id: str = Field(min_length=1)
    boundaries: tuple[int, ...] = Field(min_length=1)
    personas: tuple[str, ...] = Field(min_length=1)
    seed: int = Field(ge=0)


class ReactionRow(BaseModel):
    cohort_id: str = Field(min_length=1)
    boundary: int = Field(ge=1)
    persona_id: str = Field(min_length=1)
    variant_id: str = Field(min_length=1)
    score: float
    prompt_version: str = Field(min_length=1)
    synthetic: Literal[True] = True


class CohortEvaluation(BaseModel):
    presented_variant_ids: tuple[str, ...]
    original_variant_ids: tuple[str, ...]
    seed: int
    synthetic: Literal[True] = True


class RetrievalQuery(BaseModel):
    text: str = Field(min_length=1)
    series_id: str = Field(min_length=1)
    version_id: str = Field(min_length=1)
    language: str = Field(min_length=2)
    allowed_source_ids: tuple[str, ...]
    limit: int = Field(ge=1, le=50)


class RetrievalHit(BaseModel):
    source_id: str
    series_id: str
    version_id: str
    language: str
    text: str
    score: float
    permitted: bool = True
    citation: SourceCitation | None = None


def terms(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-zA-Z']+", text.lower()) if len(word) > 2}
