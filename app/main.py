from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import app.demo_mode as demo_mode
from app.corpus import normalize_within_book
from app.demo_mode import golden_path
from app.evaluation import EndToEndReport, evaluate_series
from app.features import FeatureExtractor
from app.heuristic_extractor import HeuristicExtractor
from app.ledger import LedgerResolver, LedgerSummary
from app.manifest import load_manifest
from app.narrative_models import ResolvedEntry, Series
from app.predictor import ContinuationPredictor
from app.rewrite import EditAttribution, RewriteReport, attribute_delta
from app.series_loader import load_series
from app.training_corpus import generate_synthetic_corpus

SERIES_PATH = Path("data/series/last_monsoon.json")
MANIFEST_PATH = Path("data/manifest/last_monsoon.yaml")

# Every prediction shown by this app is fit to a documented synthetic corpus
# (app/training_corpus.py), not to observed reader behaviour. Repeated on
# every response that carries a prediction so the number can never be read as
# measured retention -- see the README honesty section.
PREDICTION_DISCLOSURE = (
    "This prediction is from a model trained on a synthetic corpus "
    "(app/training_corpus.py) with a fully documented generative process, "
    "not on observed reader or listener behaviour. It demonstrates the "
    "pipeline end to end; it is not a calibrated real-audience number."
)

_inference_executor = ThreadPoolExecutor(max_workers=2)


class AuditResponse(BaseModel):
    series_id: str
    headline: dict[str, int]
    findings: list[ResolvedEntry]


class RewriteRequest(BaseModel):
    before_episode: int
    after_episode: int
    edits: list[EditAttribution]


@lru_cache(maxsize=1)
def _series_cached() -> Series:
    return load_series(SERIES_PATH)


def _series() -> Series:
    """A private, request-safe copy of the cached series.

    ``LedgerResolver`` can write to ``PayoffLink.verified`` during resolution,
    and pydantic models are mutable, so handing every request the exact same
    cached instance is a live cross-request corruption risk. Deep-copy at the
    cache boundary instead of inside every caller.
    """
    return _series_cached().model_copy(deep=True)


@lru_cache(maxsize=1)
def _resolved_cached() -> tuple[ResolvedEntry, ...]:
    # Resolve a copy, not the cached series. The default resolver has no verifier
    # and so never writes `PayoffLink.verified` today -- but the moment one is
    # configured, resolving the shared instance would permanently mark the
    # process-wide series on the very first call, which is the corruption
    # `_series()` exists to prevent.
    return tuple(LedgerResolver().resolve_series(_series()))


def _resolved() -> tuple[ResolvedEntry, ...]:
    return tuple(item.model_copy(deep=True) for item in _resolved_cached())


@lru_cache(maxsize=1)
def _discrimination_report() -> EndToEndReport:
    """Both numbers, computed once at startup rather than per request.

    ``ledger`` scores the authored graph as-is (traversal only); ``extracted``
    runs the offline ``HeuristicExtractor`` over the series' own episode text
    first and scores what it rebuilds. ``_series()`` hands back a private
    deep copy, so `evaluate_series`'s internal `LedgerResolver.resolve_series`
    calls -- which can write `PayoffLink.verified` -- never touch the
    process-wide cached series, for the same reason `_resolved_cached` does
    not resolve it directly (see `_series`'s docstring).
    """
    return evaluate_series(_series(), load_manifest(MANIFEST_PATH), HeuristicExtractor())


@lru_cache(maxsize=1)
def _predictor() -> ContinuationPredictor:
    """Train once at startup (first use), not per request.

    Trained on the documented synthetic corpus -- see PREDICTION_DISCLOSURE
    and README -- so the pipeline runs end to end without a real reader-
    retention dataset, which does not exist in this repo.
    """
    predictor = ContinuationPredictor()
    rows = normalize_within_book(generate_synthetic_corpus())
    predictor.train(rows)
    return predictor


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

    @app.get("/api/discrimination", response_model=EndToEndReport)
    def discrimination() -> EndToEndReport:
        return _discrimination_report()

    @app.get("/api/predict")
    def predict(episode: int = Query(ge=1)) -> dict:
        series = _series()
        # A boundary past the finale does not exist. Unbounded, the extractor
        # happily reports an obligation age in the tens of thousands and the
        # model renders a confident percentage for it.
        if episode > series.total_episodes:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"episode {episode} is past the end of the series "
                    f"({series.total_episodes} episodes)"
                ),
            )
        features = FeatureExtractor().extract(series, episode)
        predictor = _predictor()

        future = _inference_executor.submit(predictor.predict, features)
        try:
            prediction = future.result(timeout=demo_mode.INFERENCE_TIMEOUT_SECONDS)
        except FutureTimeoutError:
            # Wired-up offline fallback: a slow inference call genuinely
            # switches to the golden path rather than blocking or erroring.
            return {
                "episode": episode,
                "features": features.to_vector(),
                "prediction": None,
                "degraded": True,
                "fallback": golden_path(),
                "disclosure": PREDICTION_DISCLOSURE,
            }

        return {
            "episode": episode,
            "features": features.to_vector(),
            "prediction": prediction.model_dump(),
            "degraded": False,
            "disclosure": PREDICTION_DISCLOSURE,
        }

    @app.post("/api/rewrite", response_model=RewriteReport)
    def rewrite(payload: RewriteRequest) -> RewriteReport:
        """Attribute a rewrite's predicted movement to named edits.

        `total_delta` is never taken from the caller -- both predictions come
        from the same trained predictor, so the number being attributed is
        guaranteed to have come from the frozen model rather than a
        caller-supplied claim.
        """
        series = _series()
        for label, episode in (
            ("before_episode", payload.before_episode),
            ("after_episode", payload.after_episode),
        ):
            if not 1 <= episode <= series.total_episodes:
                raise HTTPException(
                    status_code=422,
                    detail=f"{label} {episode} is outside episodes 1-{series.total_episodes}",
                )
        # Running the window backwards inverts the comparison: obligations
        # un-accumulate, so a regression reads as a repair.
        if payload.after_episode < payload.before_episode:
            raise HTTPException(
                status_code=422,
                detail="after_episode must not precede before_episode",
            )

        predictor = _predictor()
        before_features = FeatureExtractor().extract(series, payload.before_episode)
        after_features = FeatureExtractor().extract(series, payload.after_episode)
        before_prediction = predictor.predict(before_features)
        after_prediction = predictor.predict(after_features)
        total_delta = after_prediction.value - before_prediction.value
        try:
            return attribute_delta(before_features, after_features, payload.edits, total_delta)
        except ValueError as exc:
            # An edit that names a feature which did not move, or moved the
            # wrong way for a repair, is a fabricated attribution -- reject it
            # at the API boundary rather than letting it render on screen.
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    app.mount("/", StaticFiles(directory="app/static", html=True), name="dashboard")
    return app


app = create_app()
