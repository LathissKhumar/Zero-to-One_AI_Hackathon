from __future__ import annotations

from pathlib import Path

from app.manifest import DiscriminationReport, ManifestItem, load_manifest, score_discrimination
from app.narrative_models import LedgerEntry, ResolvedEntry

MANIFEST_PATH = Path("data/manifest/last_monsoon.yaml")


def resolved(entry_id: str, state: str, overdue: bool = False) -> ResolvedEntry:
    return ResolvedEntry(
        entry=LedgerEntry(id=entry_id, kind="contradiction", description="", episodes=[1]),
        state=state,
        overdue=overdue,
    )


def test_manifest_has_all_four_defect_classes():
    manifest = load_manifest(MANIFEST_PATH)
    classes = {item.defect_class for item in manifest.items}
    assert classes == {
        "accidental_hole",
        "intentional_twist",
        "outstanding_obligation",
        "clean_control",
    }
    assert len(manifest.items) == 20


def test_perfect_agreement_scores_high_but_is_never_asserted_equal_to_one():
    manifest = load_manifest(MANIFEST_PATH)
    perfect = [resolved(item.defect_id, item.expected_state) for item in manifest.items]
    report = score_discrimination(manifest, perfect)
    assert report.recall > 0.9
    assert report.precision > 0.9
    assert report.false_positive_rate < 0.1


def test_protecting_a_real_hole_costs_recall():
    manifest = load_manifest(MANIFEST_PATH)
    sloppy = [
        resolved(item.defect_id, "suspended" if item.defect_class == "accidental_hole" else item.expected_state)
        for item in manifest.items
    ]
    report = score_discrimination(manifest, sloppy)
    assert report.holes_caught == 0
    assert report.recall == 0.0


def test_flagging_a_twist_costs_precision():
    manifest = load_manifest(MANIFEST_PATH)
    naive = [
        resolved(item.defect_id, "broken" if item.defect_class == "intentional_twist" else item.expected_state)
        for item in manifest.items
    ]
    report = score_discrimination(manifest, naive)
    assert report.twists_protected == 0
    assert report.precision < 0.6


def test_baseline_flag_count_exceeds_real_defects():
    """The gap between these numbers is the demo."""
    manifest = load_manifest(MANIFEST_PATH)
    perfect = [resolved(item.defect_id, item.expected_state) for item in manifest.items]
    report = score_discrimination(manifest, perfect)
    assert report.baseline_flags > report.holes_caught
