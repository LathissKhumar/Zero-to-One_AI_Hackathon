"""Episode text -> dual-layer graph.

The only model-driven path into the ledger. Everything downstream is
deterministic, so extraction quality is the system's ceiling.

Runs as one batched ai_query over Delta rows rather than N sequential calls --
at 300 episodes that difference is what makes series-scale analysis tractable.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field, ValidationError

from app.narrative_models import Excerpt, LedgerEntry, NarrativeNode, PayoffLink
from app.extraction_models import ExtractionContext, ExtractionFailure, ExtractionRunMetadata, SourceCitation


class ExtractionResult(BaseModel):
    nodes: list[NarrativeNode] = Field(default_factory=list)
    entries: list[LedgerEntry] = Field(default_factory=list)
    payoffs: list[PayoffLink] = Field(default_factory=list)
    excerpts: list[Excerpt] = Field(default_factory=list)
    rejected: int = 0
    # None for extractors with no notion of a backend (FakeExtractor,
    # HeuristicExtractor, DatabricksExtractor's own SQL path). LLMExtractor
    # sets this to "databricks" or "openai" so a number produced off-platform
    # can never be silently presented as the governed on-platform result.
    backend: str | None = None
    citations: list[SourceCitation] = Field(default_factory=list)
    metadata: ExtractionRunMetadata | None = None
    failures: list[ExtractionFailure] = Field(default_factory=list)

    def retryable_failures(self) -> list[ExtractionFailure]:
        return [failure for failure in self.failures if failure.retryable]


def attach_provenance(
    result: ExtractionResult,
    episodes: list[dict],
    context: ExtractionContext,
    *,
    run_id: str | None = None,
    started_at: datetime | None = None,
    latency_ms: float | None = None,
    attempt: int = 1,
) -> ExtractionResult:
    """Bind every extracted excerpt to an immutable source version."""
    source_text = {
        int(row["episode"]): str(row.get("synopsis") or row.get("body") or "")
        for row in episodes
        if isinstance(row, dict) and row.get("episode") is not None
    }
    result.citations = [
        SourceCitation.from_text(
            series_id=context.series_id,
            version_id=context.version_id,
            episode_number=excerpt.episode,
            text=source_text.get(excerpt.episode, excerpt.text),
        )
        for excerpt in result.excerpts
    ]
    started = started_at or datetime.now(timezone.utc)
    elapsed = latency_ms if latency_ms is not None else 0.0
    result.metadata = ExtractionRunMetadata(
        run_id=run_id or f"extract-{context.version_id}-{context.source_hash[:8]}",
        source_hash=context.source_hash,
        version_id=context.version_id,
        model_name=context.model_name,
        prompt_version=context.prompt_version,
        started_at=started,
        finished_at=started,
        latency_ms=elapsed,
        attempt=attempt,
    )
    return result


class Extractor(Protocol):
    def extract(self, episodes: list[dict]) -> ExtractionResult: ...


def parse_extraction_row(raw: str) -> dict | None:
    """Parse one model response. Returns None on malformed output.

    Models occasionally emit prose around JSON or truncate mid-object. Dropping
    the row keeps the batch alive; the resulting graph is partial, which the
    ledger handles, rather than absent, which it does not.
    """
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


class FakeExtractor:
    """Deterministic extractor for tests and offline demo mode."""

    def extract(self, episodes: list[dict]) -> ExtractionResult:
        nodes: list[NarrativeNode] = []
        excerpts: list[Excerpt] = []
        for row in episodes:
            episode = int(row["episode"])
            text = row.get("synopsis") or row.get("body") or ""
            nodes.append(
                NarrativeNode(
                    id=f"n-{episode}",
                    episode=episode,
                    perceived_index=episode,
                    summary=text[:200],
                    excerpt_id=f"ex-{episode}",
                )
            )
            excerpts.append(Excerpt(id=f"ex-{episode}", episode=episode, text=text))
        return ExtractionResult(nodes=nodes, excerpts=excerpts)


class DatabricksExtractor:
    """Batched ai_query extraction over a Delta episodes table.

    ``connection`` is a caller-supplied DB-API connection already scoped to a
    warehouse (e.g. a databricks-sql-connector connection built from
    warehouse/http-path config); this class never constructs one itself, so it
    never sees or hardcodes warehouse credentials or IDs.
    """

    def __init__(self, connection, catalog: str, schema: str, model: str) -> None:
        self._connection = connection
        self._catalog = catalog
        self._schema = schema
        self._model = model

    def extract(self, episodes: list[dict]) -> ExtractionResult:
        if not episodes:
            # No episodes means no series to query -- issuing the statement
            # would either bind an empty/absent series_id or scan unfiltered.
            # An empty result is the honest answer, not a query.
            return ExtractionResult()

        series_id = episodes[0]["series_id"]

        sql = (
            Path(__file__).parent.parent / "sql" / "extract_graph.sql"
        ).read_text(encoding="utf-8")
        statement = (
            sql.replace("${catalog}", self._catalog)
            .replace("${db}", self._schema)
            .replace("${model}", self._model)
        )
        with self._connection.cursor() as cursor:
            cursor.execute(statement, {"series_id": series_id})
            rows = cursor.fetchall()

        result = ExtractionResult()
        for row in rows:
            parsed = parse_extraction_row(row[0])
            if parsed is None:
                result.rejected += 1
                continue
            # A row that is valid JSON but schema-invalid (missing field, wrong
            # type on urgency/valence, etc.) is rejected wholesale rather than
            # item-by-item: a single malformed item makes the rest of that row's
            # bookkeeping suspect too, and the row-level `rejected` counter
            # already communicates "this row's contribution is missing" to the
            # ledger. The batch itself still continues.
            try:
                nodes = [NarrativeNode.model_validate(item) for item in parsed.get("nodes", [])]
                entries = [LedgerEntry.model_validate(item) for item in parsed.get("entries", [])]
                # The model cannot self-authorize a payoff. Verification is a
                # separate graph step and must remain false at this seam.
                payoffs = [
                    PayoffLink.model_validate({**item, "verified": False})
                    for item in parsed.get("payoffs", [])
                ]
                excerpts = [Excerpt.model_validate(item) for item in parsed.get("excerpts", [])]
            except ValidationError:
                result.rejected += 1
                continue
            result.nodes.extend(nodes)
            result.entries.extend(entries)
            result.payoffs.extend(payoffs)
            result.excerpts.extend(excerpts)
        return result
