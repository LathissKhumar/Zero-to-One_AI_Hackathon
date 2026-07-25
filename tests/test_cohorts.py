from __future__ import annotations

from app.cohorts import COHORTS, blind_variants, divergence_by_episode


def test_five_cohorts_weight_different_things():
    assert len(COHORTS) == 5
    weights = [tuple(sorted(cohort.weights.items())) for cohort in COHORTS]
    assert len(set(weights)) == 5, "cohorts must differ structurally, not just in prose"


def test_blinding_strips_the_variant_label():
    rows = [
        {"id": 1, "variant": "original", "text": "a"},
        {"id": 2, "variant": "rewrite", "text": "b"},
    ]
    blinded = blind_variants(rows, seed=1)
    assert all("variant" not in row for row in blinded)
    assert all(row["variant_blinded"] is True for row in blinded)
    assert {row["id"] for row in blinded} == {1, 2}


def test_divergence_finds_where_cohorts_disagree():
    """A scene everyone dislikes is weak. A scene one cohort dislikes is a
    trade-off the writer should make deliberately."""
    reactions = [
        {"episode": 12, "cohort_id": "mystery", "engagement": 0.2},
        {"episode": 12, "cohort_id": "binge", "engagement": 0.9},
        {"episode": 13, "cohort_id": "mystery", "engagement": 0.8},
        {"episode": 13, "cohort_id": "binge", "engagement": 0.85},
    ]
    divergence = divergence_by_episode(reactions)
    assert divergence[12] > divergence[13]
