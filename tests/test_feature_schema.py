from __future__ import annotations

import pytest

from app.feature_schema import FEATURE_ORDER, FEATURE_SCHEMA_VERSION, encode_features


def test_feature_order_is_canonical():
    assert FEATURE_ORDER == (
        "open_obligation_count", "mean_urgency", "min_payoff_distance",
        "mean_payoff_distance", "planting_recency", "suspended_edge_density",
        "broken_edge_count", "fair_clue_density", "sentiment_velocity",
        "perceived_time_jump", "character_thread_count",
    )


def test_missing_numeric_feature_is_rejected():
    values = {name: 0.0 for name in FEATURE_ORDER if name != "fair_clue_density"}
    with pytest.raises(ValueError, match="fair_clue_density"):
        encode_features(values, platform="arxiv")


def test_feature_vector_serializes_schema_and_platform():
    values = {name: 0.0 for name in FEATURE_ORDER}
    vector = encode_features(values, platform="arxiv")
    assert vector.schema_version == FEATURE_SCHEMA_VERSION
    assert vector.platform == "arxiv"
    assert vector.values == (0.0,) * len(FEATURE_ORDER)
