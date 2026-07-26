from __future__ import annotations

from app.narrative_models import Excerpt, LedgerEntry, NarrativeNode, Series
from app.surfaces import (
    DebtBoardQuery,
    HandoffQuery,
    LocalizationChecker,
    LocalizationEpisode,
)


def _series(series_id: str, writer: str = "writer-a") -> Series:
    return Series(
        id=series_id,
        title=series_id,
        genre="thriller",
        total_episodes=3,
        ongoing=True,
        nodes=[NarrativeNode(id="n1", episode=1, perceived_index=1, summary="The red locket is found.", entities=["Asha"], excerpt_id="x1")],
        entries=[LedgerEntry(id="p1", kind="promise", description="Find the locket", episodes=[1], urgency=5, entities=["Asha"], excerpt_ids=["x1"])],
        excerpts=[Excerpt(id="x1", episode=1, text="The red locket is found.")],
    )


def test_handoff_filters_by_writer_boundary_and_keeps_citations():
    series = _series("one")
    sheet = HandoffQuery().for_writer(series, "writer-b", 2, {1: "writer-a", 2: "writer-b"})
    assert sheet.writer_id == "writer-b"
    assert sheet.horizon == 2
    assert sheet.inherited[0].entry.id == "p1"
    assert sheet.inherited[0].citations[0].id == "x1"


def test_debt_board_does_not_merge_series_ids():
    board = DebtBoardQuery().aggregate([(_series("one"), {1: "a"}), (_series("two"), {1: "b"})])
    assert {row.series_id for row in board.items} == {"one", "two"}
    assert board.total_open == 2


def test_localization_reports_translation_drift_without_mutating_source():
    source = _series("one").excerpts[0]
    translated = LocalizationEpisode(episode=1, language="hi", text="The blue locket is found.")
    report = LocalizationChecker().check(source, translated, _series("one"))
    assert report.language == "hi"
    assert any("colour" in finding.dimension for finding in report.findings)
    assert report.findings[0].citation_ids == ["x1", "translation-hi-1"]
    assert source.text == "The red locket is found."
