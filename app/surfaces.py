"""Writer-facing read models over the shared ledger.

These queries deliberately accept a ``Series`` rather than reaching into the
demo singleton.  The same code therefore works for a submitted version and a
Unity Catalog-loaded version, while every answer retains its horizon and
citations.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel, Field

from app.ledger import LedgerResolver
from app.narrative_models import Excerpt, ResolvedEntry, Series


class HandoffSheet(BaseModel):
    series_id: str
    writer_id: str
    horizon: int
    inherited: list[ResolvedEntry] = Field(default_factory=list)
    overdue: list[ResolvedEntry] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    source_version: str


class HandoffQuery:
    def for_writer(
        self, series: Series, writer_id: str, horizon: int, writer_by_episode: dict[int, str] | None = None
    ) -> HandoffSheet:
        if horizon < 1 or horizon > series.total_episodes:
            raise ValueError("horizon must be within the published series")
        assignments = writer_by_episode or {
            int(episode): writer for episode, writer in series.episode_writers.items()
        }
        # The selected writer is allowed to inherit work from every previous
        # writer. The map is used to document who last owned the source claim,
        # not to hide obligations authored by somebody else.
        _ = assignments
        resolved = [item for item in LedgerResolver().resolve_series(series, as_of=horizon) if item.state != "paid"]
        if assignments:
            resolved = [item for item in resolved if assignments.get(item.entry.origin_episode, "unknown") != writer_id]
        overdue = [item for item in resolved if item.overdue]
        actions = [
            f"Resolve {item.entry.id} before publishing the next episode"
            for item in sorted(resolved, key=lambda item: (-item.entry.urgency, item.entry.origin_episode))
        ]
        return HandoffSheet(
            series_id=series.id,
            writer_id=writer_id,
            horizon=horizon,
            inherited=resolved,
            overdue=overdue,
            next_actions=actions,
            source_version=series.source_version,
        )


class DebtBoardItem(BaseModel):
    series_id: str
    title: str
    genre: str
    writer_id: str
    entry: ResolvedEntry
    risk: float
    source_version: str


class DebtBoard(BaseModel):
    """`narrative_debt_index` is the mean per-item `risk` across all open
    entries on the board (0.0 when empty) -- the spec names this NDI without
    defining a formula; this is the explicit, stated one."""

    items: list[DebtBoardItem] = Field(default_factory=list)
    total_open: int
    narrative_debt_index: float = 0.0
    filters: dict[str, str | int | None] = Field(default_factory=dict)


class DebtBoardQuery:
    def aggregate(
        self,
        series_and_writers: Iterable[tuple[Series, dict[int, str]]],
        *,
        series_ids: set[str] | None = None,
        writer_id: str | None = None,
        urgency: int | None = None,
        state: str | None = None,
        genre: str | None = None,
        horizon: int | None = None,
    ) -> DebtBoard:
        items: list[DebtBoardItem] = []
        for series, writer_by_episode in series_and_writers:
            if series_ids is not None and series.id not in series_ids:
                continue
            if genre is not None and series.genre != genre:
                continue
            boundary = horizon or series.total_episodes
            resolved = LedgerResolver().resolve_series(series, as_of=min(boundary, series.total_episodes))
            for entry in resolved:
                if entry.state == "paid":
                    continue
                if state is not None and entry.state != state:
                    continue
                if urgency is not None and entry.entry.urgency != urgency:
                    continue
                owner = writer_by_episode.get(entry.entry.origin_episode, "unknown")
                if writer_id is not None and owner != writer_id:
                    continue
                age = max(0, boundary - entry.entry.origin_episode)
                risk = float(entry.entry.urgency * (1 + age / 10) + (10 if entry.overdue else 0))
                items.append(DebtBoardItem(series_id=series.id, title=series.title, genre=series.genre, writer_id=owner, entry=entry, risk=risk, source_version=series.source_version))
        items.sort(key=lambda item: (-item.risk, item.series_id, item.entry.entry.id))
        ndi = sum(item.risk for item in items) / len(items) if items else 0.0
        return DebtBoard(
            items=items,
            total_open=len(items),
            narrative_debt_index=ndi,
            filters={"writer_id": writer_id, "state": state, "genre": genre, "urgency": urgency},
        )


class LocalizationEpisode(BaseModel):
    episode: int = Field(ge=1)
    language: str = Field(min_length=2, max_length=16)
    text: str = Field(min_length=1)


class LocalizationFinding(BaseModel):
    dimension: str
    severity: Literal["warning", "error"]
    message: str
    citation_ids: list[str] = Field(default_factory=list)


class LocalizationReport(BaseModel):
    series_id: str
    episode: int
    language: str
    source_version: str
    translated_excerpt_id: str
    findings: list[LocalizationFinding] = Field(default_factory=list)
    source_story_findings: list[ResolvedEntry] = Field(default_factory=list)


_NUMBER = re.compile(r"\b\d+(?:\.\d+)?\b")
_COLOURS = {"red", "blue", "green", "black", "white", "yellow", "gold", "silver"}
_TEMPORAL = {"yesterday", "today", "tomorrow", "dawn", "night", "morning", "evening"}


class LocalizationChecker:
    def check(self, source_excerpt: Excerpt, translated: LocalizationEpisode, series: Series) -> LocalizationReport:
        findings: list[LocalizationFinding] = []
        translated_id = f"translation-{translated.language}-{translated.episode}"
        citation_ids = [source_excerpt.id, translated_id]
        source_words = set(re.findall(r"[A-Za-z]+", source_excerpt.text.lower()))
        translated_words = set(re.findall(r"[A-Za-z]+", translated.text.lower()))
        source_colours = source_words & _COLOURS
        translated_colours = translated_words & _COLOURS
        if source_colours != translated_colours:
            findings.append(LocalizationFinding(dimension="colour", severity="warning", message=f"source colours {sorted(source_colours)} differ from translation {sorted(translated_colours)}", citation_ids=citation_ids))
        source_numbers = _NUMBER.findall(source_excerpt.text)
        if source_numbers != _NUMBER.findall(translated.text):
            findings.append(LocalizationFinding(dimension="numbers", severity="error", message="numeric facts differ between source and translation", citation_ids=citation_ids))
        source_temporal = source_words & _TEMPORAL
        if source_temporal and not source_temporal & translated_words:
            findings.append(LocalizationFinding(dimension="temporal_marker", severity="warning", message="the translation drops a source temporal marker", citation_ids=citation_ids))
        names = {node_entity.lower() for node in series.nodes if node.episode == source_excerpt.episode for node_entity in node.entities}
        if names and not names & translated_words:
            findings.append(LocalizationFinding(dimension="entity_name", severity="error", message="the translation does not preserve a named entity from the source episode", citation_ids=citation_ids))
        source_findings = [
            item for item in LedgerResolver().resolve_series(series, as_of=source_excerpt.episode)
            if source_excerpt.episode in item.entry.episodes and item.state != "paid"
        ]
        return LocalizationReport(series_id=series.id, episode=translated.episode, language=translated.language, source_version=series.source_version, translated_excerpt_id=translated_id, findings=findings, source_story_findings=source_findings)
