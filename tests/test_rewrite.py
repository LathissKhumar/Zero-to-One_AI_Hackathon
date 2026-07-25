# tests/test_rewrite.py
from __future__ import annotations

import pytest

from app.rewrite import EditAttribution, attribute_delta
from app.narrative_models import BoundaryFeatures


def features(**overrides) -> BoundaryFeatures:
    base = {"episode": 100, "open_obligation_count": 5, "mean_urgency": 3.0}
    return BoundaryFeatures(**{**base, **overrides})


def test_every_edit_names_the_obligation_it_discharges():
    """An edit that cannot name its ledger target is noise and must be dropped."""
    with pytest.raises(ValueError, match="must discharge"):
        EditAttribution(
            hunk="- Rafi confessed.\n+ Rafi hesitated.",
            obligation_id="",
            feature_moved="open_obligation_count",
            delta=0.05,
        )


def test_attribution_sums_to_the_observed_delta():
    before = features(open_obligation_count=5)
    after = features(open_obligation_count=3)
    edits = [
        EditAttribution(hunk="a", obligation_id="p-1", feature_moved="open_obligation_count", delta=0.04),
        EditAttribution(hunk="b", obligation_id="p-2", feature_moved="open_obligation_count", delta=0.03),
    ]
    report = attribute_delta(before, after, edits, total_delta=0.07)
    assert report.total_delta == pytest.approx(0.07)
    assert report.attributed_delta == pytest.approx(0.07)
    assert report.unattributed == pytest.approx(0.0)


def test_unattributed_movement_is_reported_not_hidden():
    """Silently absorbing unexplained movement is how a tool starts lying."""
    before = features(open_obligation_count=5)
    after = features(open_obligation_count=4)
    edits = [EditAttribution(hunk="a", obligation_id="p-1", feature_moved="open_obligation_count", delta=0.04)]
    report = attribute_delta(before, after, edits, total_delta=0.10)
    assert report.unattributed == pytest.approx(0.06)


def test_edit_rejects_a_feature_name_not_in_the_model_s_feature_order():
    """A bogus feature_moved must never be accepted -- it would let a caller
    attribute movement to a feature the model never saw."""
    with pytest.raises(ValueError, match="not a recognised feature"):
        EditAttribution(
            hunk="a",
            obligation_id="p-1",
            feature_moved="NOT_A_FEATURE",
            delta=9.99,
        )


def test_attribute_delta_rejects_an_edit_whose_named_feature_never_moved():
    """Claiming credit for a feature that is identical before and after is
    fabricated attribution."""
    before = features(open_obligation_count=5)
    after = features(open_obligation_count=5)
    edits = [EditAttribution(hunk="a", obligation_id="p-1", feature_moved="open_obligation_count", delta=0.04)]
    with pytest.raises(ValueError, match="did not move"):
        attribute_delta(before, after, edits, total_delta=0.04)


def test_attribute_delta_rejects_a_repair_whose_failure_count_got_worse():
    """broken_count and its siblings count actual failures: an increase is
    definitionally a regression, never a repair. Claiming a positive delta
    while the named failure count went up must be rejected."""
    before = features(broken_count=0)
    after = features(broken_count=1)
    edits = [EditAttribution(hunk="a", obligation_id="p-1", feature_moved="broken_count", delta=0.02)]
    with pytest.raises(ValueError, match="got worse"):
        attribute_delta(before, after, edits, total_delta=0.02)
