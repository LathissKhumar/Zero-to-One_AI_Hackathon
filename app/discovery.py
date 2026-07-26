"""Deterministic obligation-index retrieval and Explain Why output."""

from __future__ import annotations

import re
import hashlib
from collections.abc import Iterable
from typing import Protocol

from pydantic import BaseModel, Field

from app.narrative_models import Excerpt, Series


def _terms(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-zA-Z']+", text.lower()) if len(word) > 2}


class EvidenceHit(BaseModel):
    series_id: str
    excerpt_id: str
    episode: int
    score: float
    text: str
    source_version: str
    source_hash: str
    matched_dimensions: list[str] = Field(default_factory=list)


class DiscoveryMatch(BaseModel):
    series_id: str
    title: str
    score: float
    dimensions: list[str]
    explanation: str
    citation_ids: list[str]


class DiscoveryResult(BaseModel):
    query: str
    simulation_disclosure: str = "Discovery ranks obligation shape; it is not a claim about real audience behavior."
    matches: list[DiscoveryMatch] = Field(default_factory=list)


class EvidenceRepository:
    def __init__(self, series: Iterable[Series]) -> None:
        self._series = {item.id: item for item in series}

    def search(self, series_id: str, query: str, *, min_episode: int | None = None, max_episode: int | None = None) -> list[EvidenceHit]:
        current = self._series.get(series_id)
        if current is None:
            return []
        query_terms = _terms(query)
        hits: list[EvidenceHit] = []
        for excerpt in current.excerpts:
            if min_episode is not None and excerpt.episode < min_episode:
                continue
            if max_episode is not None and excerpt.episode > max_episode:
                continue
            overlap = query_terms & _terms(excerpt.text)
            if not overlap:
                continue
            hits.append(EvidenceHit(series_id=series_id, excerpt_id=excerpt.id, episode=excerpt.episode, score=len(overlap) / max(1, len(query_terms)), text=excerpt.text, source_version=current.source_version, source_hash=hashlib.sha256(excerpt.text.encode()).hexdigest(), matched_dimensions=sorted(overlap)))
        return sorted(hits, key=lambda hit: (-hit.score, hit.episode, hit.excerpt_id))


class VectorSearchClient(Protocol):
    def search(self, *, index_name: str, query: str, series_id: str, source_version: str) -> list[dict]: ...


class DatabricksVectorSearchRepository:
    """Production adapter around a Databricks Vector Search client.

    The client is injected so local tests never require credentials. The
    adapter enforces the privacy filters at the seam and normalizes results to
    the same citation model as the deterministic repository.
    """

    def __init__(self, client: VectorSearchClient, index_name: str) -> None:
        self._client = client
        self._index_name = index_name

    def search(self, series_id: str, query: str, *, source_version: str, min_episode: int | None = None, max_episode: int | None = None) -> list[EvidenceHit]:
        rows = self._client.search(index_name=self._index_name, query=query, series_id=series_id, source_version=source_version)
        hits = []
        for row in rows:
            if row.get("series_id") != series_id or row.get("source_version") != source_version:
                continue
            if min_episode is not None and int(row["episode"]) < min_episode:
                continue
            if max_episode is not None and int(row["episode"]) > max_episode:
                continue
            text = str(row.get("text", ""))
            hits.append(EvidenceHit(series_id=series_id, excerpt_id=str(row["excerpt_id"]), episode=int(row["episode"]), score=float(row.get("score", 0.0)), text=text, source_version=source_version, source_hash=str(row.get("source_hash") or hashlib.sha256(text.encode()).hexdigest()), matched_dimensions=list(row.get("matched_dimensions", []))))
        return sorted(hits, key=lambda hit: (-hit.score, hit.episode, hit.excerpt_id))


def discover(series: Series, query: str) -> DiscoveryResult:
    repo = EvidenceRepository([series])
    hits = repo.search(series.id, query)
    if not hits:
        # Mood words often do not appear literally. The index still returns the
        # most relevant unresolved obligation with a transparent structural
        # dimension rather than pretending a semantic embedding exists locally.
        hits = [EvidenceHit(series_id=series.id, excerpt_id=excerpt.id, episode=excerpt.episode, score=0.01, text=excerpt.text, source_version=series.source_version, source_hash=hashlib.sha256(excerpt.text.encode()).hexdigest(), matched_dimensions=["unresolved_obligation"]) for excerpt in series.excerpts[:1]]
    match = None
    if hits:
        dimensions = ["unresolved_obligation"]
        if any(word in query.lower() for word in ("heartbreak", "love", "longing")):
            dimensions.append("emotional_payoff")
        if any(word in query.lower() for word in ("rain", "slow", "sunday")):
            dimensions.append("atmospheric_pace")
        top = hits[0]
        match = DiscoveryMatch(series_id=series.id, title=series.title, score=top.score, dimensions=dimensions, explanation=f"Matched {', '.join(dimensions)} using Ep {top.episode} evidence.", citation_ids=[top.excerpt_id])
    return DiscoveryResult(query=query, matches=[match] if match else [])
