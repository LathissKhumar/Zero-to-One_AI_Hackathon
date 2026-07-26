from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.extraction import ExtractionResult
from app.extraction_models import (
    ExtractionContext,
    ExtractionFailure,
    ExtractionRunMetadata,
    SourceCitation,
)
from app.heuristic_extractor import HeuristicExtractor
from app.extraction_repository import InMemoryExtractionRunRepository
from app.ledger import Ledger
from app.narrative_models import NarrativeNode


def test_citation_rejects_span_from_another_version():
    with pytest.raises(ValueError, match="version_id"):
        SourceCitation(
            series_id="s",
            version_id="v2",
            episode_number=1,
            start_offset=0,
            end_offset=4,
            quote_hash="v1:abc",
        )


def test_metadata_rejects_finish_before_start():
    start = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="finished_at"):
        ExtractionRunMetadata(
            run_id="run-1",
            source_hash="h",
            version_id="v1",
            model_name="offline",
            prompt_version="p1",
            started_at=start,
            finished_at=start - timedelta(seconds=1),
            latency_ms=0,
            attempt=1,
        )


def test_retryable_failures_exclude_permanent_validation_errors():
    result = ExtractionResult(
        failures=[
            ExtractionFailure(code="timeout", message="slow", retryable=True),
            ExtractionFailure(code="schema", message="bad", retryable=False),
        ]
    )
    assert [failure.code for failure in result.retryable_failures()] == ["timeout"]


def test_extraction_context_carries_source_identity():
    context = ExtractionContext(
        series_id="s",
        version_id="v1",
        source_hash="h",
        model_name="offline",
        prompt_version="p1",
    )
    assert context.version_id == "v1"


def test_heuristic_adapter_returns_version_bound_citations():
    context = ExtractionContext(
        series_id="s",
        version_id="v1",
        source_hash="h",
        model_name="offline",
        prompt_version="p1",
    )
    result = HeuristicExtractor().extract(
        [{"episode": 1, "synopsis": "Asha promises to return."}], context=context
    )
    assert result.metadata is not None
    assert result.metadata.version_id == "v1"
    assert all(citation.version_id == "v1" for citation in result.citations)


def test_run_repository_upserts_rows_and_returns_only_retryable_failures():
    repository = InMemoryExtractionRunRepository()
    started = datetime.now(timezone.utc)
    result = ExtractionResult(
        metadata=ExtractionRunMetadata(
            run_id="run-1", source_hash="h", version_id="v1", model_name="offline",
            prompt_version="p1", started_at=started, finished_at=started,
            latency_ms=1, attempt=1,
        ),
        failures=[ExtractionFailure(code="timeout", message="slow", retryable=True, episode_number=2)],
    )
    repository.record_result(result)
    repository.record_result(result)
    assert len(repository.results) == 1
    assert [failure.code for failure in repository.retryable_failures("run-1")] == ["timeout"]


def test_ledger_rejects_graph_item_without_source_citation():
    result = ExtractionResult(
        nodes=[NarrativeNode(id="n-1", episode=1, perceived_index=1, summary="one")],
        metadata=ExtractionRunMetadata(
            run_id="run-1", source_hash="h", version_id="v1", model_name="offline",
            prompt_version="p1", started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc), latency_ms=1, attempt=1,
        ),
    )
    with pytest.raises(ValueError, match="citation"):
        Ledger().add_extraction(result)
