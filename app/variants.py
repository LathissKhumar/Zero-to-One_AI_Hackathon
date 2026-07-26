"""Immutable, reviewable graph variants for surgical repairs."""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, Field

from app.ledger import LedgerResolver
from app.narrative_models import Series
from app.variant_models import RepairProposal, ValidationResult, VariantOperation


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
    operation: VariantOperation | None = None
    changed_node_ids: tuple[str, ...] = ()


def validate_variant(original: Series, variant: Variant) -> ValidationResult:
    original_hash = _true_graph_hash(original)
    variant_hash = _true_graph_hash(variant.series)
    errors: list[str] = []
    if original_hash != variant_hash and variant.operation and variant.operation.kind != "repair":
        errors.append("G_true nodes or edges changed")
    if variant.base_version != original.source_version:
        errors.append("parent version mismatch")
    return ValidationResult(valid=not errors, errors=errors)


def _true_graph_hash(series: Series) -> str:
    payload = [
        {key: value for key, value in node.model_dump().items() if key != "perceived_index"}
        for node in sorted(series.nodes, key=lambda item: item.id)
    ]
    payload.extend(entry.model_dump() for entry in sorted(series.entries, key=lambda item: item.id))
    payload.extend(payoff.model_dump() for payoff in sorted(series.payoffs, key=lambda item: (item.target_id, item.episode)))
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


class RepairEngine:
    def propose(self, graph: Series, issue_id: str) -> RepairProposal:
        target = next((entry for entry in graph.entries if entry.id == issue_id), None)
        if target is None or target.kind != "contradiction":
            raise ValueError("repair proposal requires a contradiction issue")
        node = next((node for node in graph.nodes if node.episode == max(target.episodes)), None)
        if node is None:
            raise ValueError("repair issue has no target node")
        return RepairProposal(
            issue_id=issue_id,
            target_node_id=node.id,
            replacement_claim=node.summary,
            preserved_node_ids=tuple(item.id for item in graph.nodes if item.id != node.id),
            reason_codes=("targeted_node", "preserve_unaffected_graph"),
        )

    def apply(self, graph: Series, proposal: RepairProposal) -> Variant:
        return self.repair(graph, proposal.issue_id, proposal.target_node_id, proposal.replacement_claim)

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
            operation=VariantOperation(kind="repair", node_ids=(node_id,), seed=0),
            changed_node_ids=(node_id,),
        )
