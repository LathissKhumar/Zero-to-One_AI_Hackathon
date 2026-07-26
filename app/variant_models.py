"""Typed graph operations and validation results."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class VariantOperation(BaseModel):
    kind: Literal["repair", "swap_order", "hide_clue", "reveal_clue"]
    node_ids: tuple[str, ...] = Field(min_length=1)
    seed: int = Field(ge=0)


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)


class RepairProposal(BaseModel):
    issue_id: str = Field(min_length=1)
    target_node_id: str = Field(min_length=1)
    replacement_claim: str = Field(min_length=1)
    preserved_node_ids: tuple[str, ...] = Field(min_length=1)
    reason_codes: tuple[str, ...] = Field(min_length=1)


class AgentAnnotation(BaseModel):
    persona_id: str
    issue_ids: tuple[str, ...] = ()
    confidence: float = Field(ge=0.0, le=1.0)
    reason_codes: tuple[str, ...] = Field(min_length=1)
    latency_ms: float = Field(ge=0.0)
    timed_out: bool = False
