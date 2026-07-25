from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from app.demo_data import get_demo_catalogue, get_demo_story
from app.engine import NarrativeDebtEngine
from app.models import AuditResult, BenchmarkResult, DiscoveryMatch, Story


class CompareRequest(BaseModel):
    left_slug: str = Field(min_length=1)
    right_slug: str = Field(min_length=1)


def create_app() -> FastAPI:
    app = FastAPI(title="CanonPulse", version="0.1.0")
    engine = NarrativeDebtEngine()

    @app.get("/api/story", response_model=Story)
    def story() -> Story:
        return get_demo_story()

    @app.post("/api/compare", response_model=AuditResult)
    def compare(payload: CompareRequest) -> AuditResult:
        try:
            return engine.compare(get_demo_story(), payload.left_slug, payload.right_slug)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get("/api/benchmark", response_model=BenchmarkResult)
    def benchmark() -> BenchmarkResult:
        return engine.run_benchmark(get_demo_story())

    @app.get("/api/discover", response_model=list[DiscoveryMatch])
    def discover(q: str = Query(min_length=2, max_length=120)) -> list[DiscoveryMatch]:
        return engine.discover(q, get_demo_catalogue())

    return app


app = create_app()
