"""Opt-in, provenance-preserving adapters for real retention sources.

No adapter downloads data and none ships labels. A caller must provide a local
licensed export explicitly; otherwise the failure is visible instead of being
silently replaced with the synthetic fixture.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, Field


class CorpusSourceConfig(BaseModel):
    platform: str
    path: Path
    license_reference: str = Field(min_length=1)
    source_version: str = Field(min_length=1)


class CorpusAdapter:
    platform: str

    def __init__(self, config: CorpusSourceConfig) -> None:
        if config.platform != self.platform:
            raise ValueError(f"{type(self).__name__} expects platform {self.platform}")
        self.config = config

    def _read(self) -> list[dict]:
        if not self.config.path.exists():
            raise FileNotFoundError(f"licensed {self.platform} export not found: {self.config.path}")
        try:
            data = json.loads(self.config.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("corpus export must be a JSON array") from exc
        if not isinstance(data, list):
            raise ValueError("corpus export must be a JSON array")
        return data

    def _row(self, raw: dict, *, chapter: int, continue_rate: float) -> dict:
        book_id = str(raw.get("book_id", "")).strip()
        if not book_id:
            raise ValueError("corpus row has no book_id")
        return {
            "platform": self.platform,
            "book_id": book_id,
            "chapter": chapter,
            "continue_rate": float(continue_rate),
            "text_reference": str(raw.get("text_reference", "")),
            "source_version": self.config.source_version,
            "license_reference": self.config.license_reference,
        }


class ArxivAdapter(CorpusAdapter):
    platform = "arxiv"

    def load(self) -> list[dict]:
        rows = []
        for raw in self._read():
            rows.append(self._row(raw, chapter=int(raw["chapter"]), continue_rate=raw["continue_rate"]))
        return rows


class QidianAdapter(CorpusAdapter):
    platform = "qidian"

    def load(self) -> list[dict]:
        rows = []
        for raw in self._read():
            responses = float(raw.get("reader_responses", 0))
            prior = float(raw.get("prior_reader_responses", 0))
            rate = responses / prior if prior > 0 else float(raw.get("continue_rate", 0.0))
            rows.append(self._row(raw, chapter=int(raw["chapter"]), continue_rate=rate))
        return rows


class RoyalRoadAdapter(CorpusAdapter):
    platform = "royalroad"

    def load(self) -> list[dict]:
        rows = []
        for raw in self._read():
            views = float(raw["views"])
            prior = float(raw.get("prior_views", 0))
            rate = views / prior if prior > 0 else float(raw.get("continue_rate", 0.0))
            rows.append(self._row(raw, chapter=int(raw["chapter"]), continue_rate=rate))
        return rows


def source_checksum(rows: list[dict]) -> str:
    """Stable checksum for an adapter output, suitable for MLflow/Delta tags."""
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
