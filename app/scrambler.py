"""Presentation-order variants that leave the chronological graph untouched."""

from __future__ import annotations

import hashlib
import json

from app.narrative_models import Series
from app.variants import Variant


class Scrambler:
    @staticmethod
    def graph_hash(series: Series) -> str:
        payload = [
            {key: value for key, value in node.model_dump().items() if key != "perceived_index"}
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
        )

