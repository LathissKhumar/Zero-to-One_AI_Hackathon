"""Surgical repair and the attribution that justifies it.

Two rules keep this from becoming generic LLM rewriting:

1. Every edit must name the ledger obligation it discharges. An edit that cannot
   is dropped -- that constraint alone removes most of what a model volunteers.
2. Movement in the prediction is decomposed per edit, and whatever cannot be
   attributed is reported rather than absorbed.
"""

from __future__ import annotations

from pydantic import BaseModel, field_validator

from app.narrative_models import BoundaryFeatures


class EditAttribution(BaseModel):
    hunk: str
    obligation_id: str
    feature_moved: str
    delta: float

    @field_validator("obligation_id")
    @classmethod
    def _must_target_an_obligation(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("every edit must discharge a named ledger obligation")
        return value


class RewriteReport(BaseModel):
    total_delta: float
    attributed_delta: float
    unattributed: float
    edits: list[EditAttribution]
    features_before: BoundaryFeatures
    features_after: BoundaryFeatures


def attribute_delta(
    before: BoundaryFeatures,
    after: BoundaryFeatures,
    edits: list[EditAttribution],
    total_delta: float,
) -> RewriteReport:
    attributed = sum(edit.delta for edit in edits)
    return RewriteReport(
        total_delta=total_delta,
        attributed_delta=attributed,
        unattributed=total_delta - attributed,
        edits=edits,
        features_before=before,
        features_after=after,
    )
