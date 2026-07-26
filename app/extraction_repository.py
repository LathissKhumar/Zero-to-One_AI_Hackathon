"""Row-level extraction run audit boundary."""

from __future__ import annotations

from app.extraction import ExtractionResult
from app.extraction_models import ExtractionFailure, ExtractionRunMetadata


class InMemoryExtractionRunRepository:
    def __init__(self) -> None:
        self.runs: dict[str, ExtractionRunMetadata] = {}
        self.results: dict[tuple[str, int | None], ExtractionResult] = {}

    def start(self, metadata: ExtractionRunMetadata) -> None:
        self.runs[metadata.run_id] = metadata

    def record_result(self, result: ExtractionResult) -> None:
        if result.metadata is None:
            raise ValueError("extraction result metadata is required")
        self.start(result.metadata)
        failures = result.failures or [ExtractionFailure(code="input", message="success", retryable=False)]
        for failure in failures:
            self.results[(result.metadata.run_id, failure.episode_number)] = result.model_copy(deep=True)

    def retryable_failures(self, run_id: str) -> list[ExtractionFailure]:
        failures: list[ExtractionFailure] = []
        for (stored_run_id, _episode), result in self.results.items():
            if stored_run_id == run_id:
                failures.extend(result.retryable_failures())
        return failures
