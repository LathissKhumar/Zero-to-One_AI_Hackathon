"""Fail-closed deterministic payoff verification."""

from __future__ import annotations

from app.narrative_models import LedgerEntry, PayoffLink, Series


class PayoffVerifier:
    """Grant contradiction protection only when graph evidence agrees."""

    def __init__(self, series: Series) -> None:
        self._series = series

    def __call__(self, link: PayoffLink, entry: LedgerEntry) -> bool:
        if link.episode <= entry.latest_episode:
            return False
        node = next((candidate for candidate in self._series.nodes if candidate.id == link.node_id), None)
        if node is None or node.episode != link.episode or not node.excerpt_id:
            return False
        if node.excerpt_id not in {excerpt.id for excerpt in self._series.excerpts}:
            return False
        if not link.rationale.strip():
            return False
        if entry.entities and node.entities and not set(entry.entities) & set(node.entities):
            return False
        return True
