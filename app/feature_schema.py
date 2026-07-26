"""Versioned structural feature contract shared by training and inference."""

from __future__ import annotations

import math
from collections.abc import Mapping

from pydantic import BaseModel, Field

FEATURE_SCHEMA_VERSION = "structural-v2"
FEATURE_ORDER: tuple[str, ...] = (
    "open_obligation_count",
    "mean_urgency",
    "min_payoff_distance",
    "mean_payoff_distance",
    "planting_recency",
    "suspended_edge_density",
    "broken_edge_count",
    "fair_clue_density",
    "sentiment_velocity",
    "perceived_time_jump",
    "character_thread_count",
)


class FeatureVector(BaseModel):
    values: tuple[float, ...] = Field(min_length=len(FEATURE_ORDER), max_length=len(FEATURE_ORDER))
    platform: str = Field(min_length=1)
    schema_version: str = FEATURE_SCHEMA_VERSION


def encode_features(raw: Mapping[str, float], platform: str) -> FeatureVector:
    missing = [name for name in FEATURE_ORDER if name not in raw]
    if missing:
        raise ValueError(f"missing feature: {missing[0]}")
    values = tuple(float(raw[name]) for name in FEATURE_ORDER)
    if any(not math.isfinite(value) for value in values):
        raise ValueError("feature values must be finite")
    return FeatureVector(values=values, platform=platform, schema_version=FEATURE_SCHEMA_VERSION)
