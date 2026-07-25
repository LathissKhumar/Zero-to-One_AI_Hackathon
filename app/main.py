from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.features import FeatureExtractor
from app.ledger import LedgerResolver, LedgerSummary
from app.manifest import DiscriminationReport, load_manifest, score_discrimination
from app.narrative_models import ResolvedEntry, Series
from app.series_loader import load_series

SERIES_PATH = Path("data/series/last_monsoon.json")
MANIFEST_PATH = Path("data/manifest/last_monsoon.yaml")


class AuditResponse(BaseModel):
    series_id: str
    headline: dict[str, int]
    findings: list[ResolvedEntry]


@lru_cache(maxsize=1)
def _series() -> Series:
    return load_series(SERIES_PATH)


@lru_cache(maxsize=1)
def _resolved() -> tuple[ResolvedEntry, ...]:
    return tuple(LedgerResolver().resolve_series(_series()))


def create_app() -> FastAPI:
    app = FastAPI(title="CanonPulse", version="0.2.0")

    @app.get("/api/series")
    def series() -> dict:
        current = _series()
        return {
            "id": current.id,
            "title": current.title,
            "genre": current.genre,
            "total_episodes": current.total_episodes,
        }

    @app.get("/api/audit", response_model=AuditResponse)
    def audit() -> AuditResponse:
        resolved = list(_resolved())
        summary = LedgerSummary(resolved)
        # Paid entries are correct behaviour, not findings -- surfacing them
        # would recreate the over-flagging this product exists to fix.
        findings = [item for item in resolved if item.state != "paid"]
        return AuditResponse(
            series_id=_series().id,
            headline=summary.headline(),
            findings=findings,
        )

    @app.get("/api/discrimination", response_model=DiscriminationReport)
    def discrimination() -> DiscriminationReport:
        return score_discrimination(load_manifest(MANIFEST_PATH), list(_resolved()))

    @app.get("/api/predict")
    def predict(episode: int = Query(ge=1)) -> dict:
        features = FeatureExtractor().extract(_series(), episode)
        return {"episode": episode, "features": features.to_vector()}

    app.mount("/", StaticFiles(directory="app/static", html=True), name="dashboard")
    return app


app = create_app()
