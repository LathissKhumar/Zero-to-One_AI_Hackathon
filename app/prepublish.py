"""Draft-only checks for a proposed next episode."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.heuristic_extractor import HeuristicExtractor
from app.ledger import LedgerResolver
from app.narrative_models import ResolvedEntry, Series
from app.predictor import Prediction


class PrePublishRequest(BaseModel):
    episode: int = Field(ge=1)
    text: str = Field(min_length=1)


class PrePublishReport(BaseModel):
    series_id: str
    source: str = "file"
    candidate_episode: int
    complete: bool
    extraction_rejected: int
    findings: list[ResolvedEntry]
    retention_delta: float | None = None
    prediction: Prediction | None = None


class PrePublishChecker:
    """Run a candidate through extraction and ledger resolution without mutation."""

    def __init__(self, extractor: HeuristicExtractor | None = None) -> None:
        self._extractor = extractor or HeuristicExtractor()

    def check(self, series: Series, request: PrePublishRequest) -> tuple[PrePublishReport, Series]:
        rows = [
            {"episode": excerpt.episode, "synopsis": excerpt.text}
            for excerpt in sorted(series.excerpts, key=lambda item: item.episode)
        ]
        rows.append({"episode": request.episode, "synopsis": request.text})
        extraction = self._extractor.extract(rows)
        candidate_series = series.model_copy(
            deep=True,
            update={
                "total_episodes": request.episode,
                "ongoing": True,
                "nodes": extraction.nodes,
                "entries": extraction.entries,
                "payoffs": extraction.payoffs,
                "excerpts": extraction.excerpts,
            },
        )
        resolved = LedgerResolver().resolve_series(candidate_series, as_of=request.episode)
        findings = [
            item
            for item in resolved
            if item.entry.latest_episode == request.episode and item.state != "paid"
        ]
        report = PrePublishReport(
            series_id=series.id,
            candidate_episode=request.episode,
            complete=extraction.rejected == 0,
            extraction_rejected=extraction.rejected,
            findings=findings,
        )
        return report, candidate_series
