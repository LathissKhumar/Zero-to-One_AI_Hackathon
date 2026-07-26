from __future__ import annotations

import pytest

from app.retrieval import LocalRetriever
from app.retrieval_models import ReactionRow, RetrievalQuery, RetrievalHit


def test_reaction_row_requires_synthetic_disclosure():
    with pytest.raises(ValueError, match="synthetic"):
        ReactionRow(
            cohort_id="c", boundary=1, persona_id="p", variant_id="v",
            score=0.4, prompt_version="p1", synthetic=False,
        )


def test_retrieval_query_requires_version_and_language():
    with pytest.raises(ValueError, match="version_id"):
        RetrievalQuery(
            text="storm", series_id="s", version_id="", language="en",
            allowed_source_ids=(), limit=5,
        )


def test_retrieval_filters_language_version_and_permissions():
    hits = [
        RetrievalHit(source_id="a", series_id="s", version_id="v1", language="en", text="storm", score=0.9, permitted=True),
        RetrievalHit(source_id="b", series_id="s", version_id="v1", language="hi", text="storm", score=0.8, permitted=True),
        RetrievalHit(source_id="c", series_id="s", version_id="v2", language="en", text="storm", score=0.7, permitted=True),
        RetrievalHit(source_id="d", series_id="s", version_id="v1", language="en", text="storm", score=0.6, permitted=False),
    ]
    retriever = LocalRetriever(hits)
    result = retriever.search(RetrievalQuery(text="storm", series_id="s", version_id="v1", language="en", allowed_source_ids=("a",), limit=5))
    assert [item.source_id for item in result] == ["a"]
