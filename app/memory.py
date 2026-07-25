"""Citation-backed Series Memory queries over one selected series version."""

from __future__ import annotations

import re

from app.ledger import LedgerResolver
from app.narrative_models import ResolvedEntry, Series

_WORD = re.compile(r"[A-Za-z0-9']+")


def _terms(value: str) -> set[str]:
    return {word.lower() for word in _WORD.findall(value) if len(word) > 1}


class MemoryQuery:
    """Search the resolved ledger without bypassing its horizon semantics."""

    def __init__(self, resolver: LedgerResolver | None = None) -> None:
        self._resolver = resolver or LedgerResolver()

    def search(self, series: Series, query: str, episode: int | None = None) -> list[ResolvedEntry]:
        requested = _terms(query)
        if not requested:
            return []
        horizon = episode if episode is not None else series.total_episodes
        excerpts = {excerpt.id: excerpt.text for excerpt in series.excerpts}
        matches: list[ResolvedEntry] = []
        for item in self._resolver.resolve_series(series, as_of=horizon):
            searchable = " ".join(
                [
                    item.entry.description,
                    *item.entry.entities,
                    *(excerpts.get(excerpt_id, "") for excerpt_id in item.entry.excerpt_ids),
                ]
            )
            if requested & _terms(searchable):
                matches.append(item)
        return sorted(matches, key=lambda item: (item.entry.origin_episode, item.entry.id))
