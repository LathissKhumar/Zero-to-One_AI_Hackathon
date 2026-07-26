from __future__ import annotations

from app.discovery import DatabricksVectorSearchRepository, EvidenceRepository, discover
from app.narrative_models import Excerpt, LedgerEntry, Series


def test_retrieval_is_series_filtered_and_explain_why_has_citations():
    series = Series(
        id="one", title="One", genre="thriller", total_episodes=2,
        entries=[LedgerEntry(id="p", kind="promise", description="unresolved longing", episodes=[1], urgency=4, excerpt_ids=["x"])],
        excerpts=[Excerpt(id="x", episode=1, text="Asha carries unresolved longing through the rain.")],
    )
    other = series.model_copy(update={"id": "two"})
    repo = EvidenceRepository([series, other])
    hits = repo.search("one", "rain longing")
    assert hits and hits[0].series_id == "one"
    result = discover(series, "rainy Sunday after heartbreak")
    assert result.matches
    assert result.matches[0].explanation
    assert result.matches[0].citation_ids == ["x"]


def test_vector_search_adapter_enforces_series_and_version_filters():
    class FakeVectorClient:
        def search(self, **kwargs):
            return [
                {"series_id": "one", "source_version": "demo", "excerpt_id": "x", "episode": 1, "score": 0.9, "text": "ok"},
                {"series_id": "two", "source_version": "demo", "excerpt_id": "private", "episode": 1, "score": 1.0, "text": "no"},
            ]

    hits = DatabricksVectorSearchRepository(FakeVectorClient(), "idx").search("one", "ok", source_version="demo")
    assert [hit.excerpt_id for hit in hits] == ["x"]
    assert hits[0].source_hash
