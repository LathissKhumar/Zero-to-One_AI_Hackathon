"""Episode text -> dual-layer graph.

The only model-driven path into the ledger. Everything downstream is
deterministic, so extraction quality is the system's ceiling.

Runs as one batched ai_query over Delta rows rather than N sequential calls --
at 300 episodes that difference is what makes series-scale analysis tractable.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field, ValidationError

from app.narrative_models import Excerpt, LedgerEntry, NarrativeNode, PayoffLink


class ExtractionResult(BaseModel):
    nodes: list[NarrativeNode] = Field(default_factory=list)
    entries: list[LedgerEntry] = Field(default_factory=list)
    payoffs: list[PayoffLink] = Field(default_factory=list)
    excerpts: list[Excerpt] = Field(default_factory=list)
    rejected: int = 0


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
                payoffs = [PayoffLink.model_validate(item) for item in parsed.get("payoffs", [])]
                excerpts = [Excerpt.model_validate(item) for item in parsed.get("excerpts", [])]
            except ValidationError:
                result.rejected += 1
                continue
            result.nodes.extend(nodes)
            result.entries.extend(entries)
            result.payoffs.extend(payoffs)
            result.excerpts.extend(excerpts)
        return result
