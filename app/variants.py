"""Immutable, reviewable graph variants for surgical repairs."""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, Field

from app.ledger import LedgerResolver
from app.narrative_models import Series


class GraphDiff(BaseModel):
    node_id: str
    before: str
    after: str
    changed_fields: list[str] = Field(default_factory=list)


class Variant(BaseModel):
    variant_id: str
    series: Series
    base_version: str
    model_version: str = "unscored"
    graph_diffs: list[GraphDiff] = Field(default_factory=list)
    discharged_entry_ids: list[str] = Field(default_factory=list)
    newly_introduced_entry_ids: list[str] = Field(default_factory=list)
    review_status: str = "needs_human_approval"
    true_graph_hash: str | None = None


class RepairEngine:
    def repair(self, source: Series, target_entry_id: str, node_id: str, replacement_summary: str) -> Variant:
        target = next((entry for entry in source.entries if entry.id == target_entry_id), None)
        if target is None:
            raise ValueError(f"unknown ledger entry: {target_entry_id}")
        if target.kind != "contradiction":
            raise ValueError("surgical repair currently targets a contradiction")
        resolved = {item.entry.id: item for item in LedgerResolver().resolve_series(source)}
        if resolved[target_entry_id].state != "broken":
            raise ValueError("only a broken entry may be repaired")
        nodes = source.model_copy(deep=True).nodes
        node = next((item for item in nodes if item.id == node_id), None)
        if node is None:
            raise ValueError(f"unknown repair node: {node_id}")
        if node.episode not in target.episodes:
            raise ValueError("repair node is unrelated to the target contradiction")
        if not replacement_summary.strip():
            raise ValueError("replacement summary cannot be empty")
        before = node.summary
        node.summary = replacement_summary
        variant_series = source.model_copy(deep=True)
        variant_series.nodes = nodes
        variant_series.entries = [entry for entry in variant_series.entries if entry.id != target_entry_id]
        variant_id = hashlib.sha256(f"{source.source_version}:{target_entry_id}:{node_id}:{replacement_summary}".encode()).hexdigest()[:16]
        return Variant(
            variant_id=variant_id,
            series=variant_series,
            base_version=source.source_version,
            graph_diffs=[GraphDiff(node_id=node_id, before=before, after=replacement_summary, changed_fields=["summary"])],
            discharged_entry_ids=[target_entry_id],
        )

