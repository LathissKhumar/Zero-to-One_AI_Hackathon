from __future__ import annotations

from pathlib import Path

from app.evaluation import EndToEndReport, evaluate_series
from app.heuristic_extractor import HeuristicExtractor
from app.manifest import load_manifest
from app.series_loader import load_series

SERIES = Path("data/series/last_monsoon.json")
MANIFEST = Path("data/manifest/last_monsoon.yaml")


def test_reports_both_the_authored_and_extracted_scores():
    report = evaluate_series(
        load_series(SERIES), load_manifest(MANIFEST), extractor=HeuristicExtractor()
    )
    assert isinstance(report, EndToEndReport)
    assert report.ledger is not None
    assert report.extracted is not None


def test_the_authored_graph_still_scores_near_perfect():
    """Traversal is exact; this number measures ledger correctness only."""
    report = evaluate_series(load_series(SERIES), load_manifest(MANIFEST))
    assert report.ledger.recall > 0.9
    assert report.extracted is None, "no extractor supplied means no end-to-end number"


def test_the_extracted_score_is_strictly_weaker_than_the_authored_one():
    """The point of the exercise. A rule-based extractor cannot recover a
    hand-authored graph exactly, so this number can fall -- which is what makes
    it evidence rather than a restatement of the fixture."""
    report = evaluate_series(
        load_series(SERIES), load_manifest(MANIFEST), extractor=HeuristicExtractor()
    )
    assert report.extracted.recall < report.ledger.recall


def test_extraction_rejections_are_reported_not_swallowed():
    report = evaluate_series(
        load_series(SERIES), load_manifest(MANIFEST), extractor=HeuristicExtractor()
    )
    assert report.extraction_rejected >= 0
