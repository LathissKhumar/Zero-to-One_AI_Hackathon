"""Presentation-order variants that leave the chronological graph untouched."""

from __future__ import annotations

import hashlib
import json

from app.narrative_models import Series
from app.variants import Variant
from app.variant_models import VariantOperation


class Scrambler:
    @staticmethod
    def graph_hash(series: Series) -> str:
        payload = [
            {key: value for key, value in node.model_dump().items() if key not in {"perceived_index", "hidden_in_perceived"}}
            for node in sorted(series.nodes, key=lambda item: item.id)
        ]
        payload += [entry.model_dump() for entry in sorted(series.entries, key=lambda item: item.id)]
        payload += [payoff.model_dump() for payoff in sorted(series.payoffs, key=lambda item: (item.target_id, item.episode))]
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def scramble(self, source: Series, presentation_order: list[int]) -> Variant:
        expected = [node.episode for node in source.nodes]
        if sorted(presentation_order) != sorted(expected) or len(presentation_order) != len(set(presentation_order)):
            raise ValueError("presentation_order must be a permutation of node episodes")
        positions = {episode: index + 1 for index, episode in enumerate(presentation_order)}
        variant_series = source.model_copy(deep=True)
        for node in variant_series.nodes:
            node.perceived_index = positions[node.episode]
        before_hash = self.graph_hash(source)
        after_hash = self.graph_hash(variant_series)
        if before_hash != after_hash:
            raise ValueError("scrambler changed the true graph")
        return Variant(
            variant_id=hashlib.sha256(f"scramble:{source.source_version}:{presentation_order}".encode()).hexdigest()[:16],
            series=variant_series,
            base_version=source.source_version,
            graph_diffs=[],
            true_graph_hash=before_hash,
            operation=VariantOperation(kind="swap_order", node_ids=tuple(node.id for node in source.nodes), seed=0),
            changed_node_ids=tuple(node.id for node in source.nodes),
        )

    def scramble_perceived(self, source: Series, operation: VariantOperation) -> Variant:
        nodes = {node.id: node for node in source.nodes}
        if any(node_id not in nodes for node_id in operation.node_ids):
            raise ValueError("scramble operation references an unknown node")
        variant_series = source.model_copy(deep=True)
        variant_nodes = {node.id: node for node in variant_series.nodes}
        if operation.kind == "swap_order":
            if len(operation.node_ids) != 2:
                raise ValueError("swap_order requires exactly two nodes")
            first, second = (variant_nodes[node_id] for node_id in operation.node_ids)
            first.perceived_index, second.perceived_index = second.perceived_index, first.perceived_index
        elif operation.kind == "hide_clue":
            for node_id in operation.node_ids:
                variant_nodes[node_id].hidden_in_perceived = True
        elif operation.kind == "reveal_clue":
            for node_id in operation.node_ids:
                variant_nodes[node_id].hidden_in_perceived = False
        before_hash = self.graph_hash(source)
        variant = Variant(
            variant_id=hashlib.sha256(f"typed:{source.source_version}:{operation.model_dump_json()}".encode()).hexdigest()[:16],
            series=variant_series,
            base_version=source.source_version,
            true_graph_hash=before_hash,
            operation=operation,
            changed_node_ids=operation.node_ids,
        )
        if self.graph_hash(variant.series) != before_hash:
            raise ValueError("scrambler changed the true graph")
        return variant
