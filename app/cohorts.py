"""Cohort reactions across the whole series.

Cohorts do not produce the headline number -- the trained regressor does. Their
job is localization: where in the series each listener type disengages, and why.
Five curves over episode index; the signal is where they diverge.

They differ by weight vector over the same structural terms, not by adjectives in
a prompt. Five personas that all sound like the same model are decoration.
"""

from __future__ import annotations

import random
from collections import defaultdict
from statistics import pstdev

from pydantic import BaseModel


class Cohort(BaseModel):
    id: str
    name: str
    weights: dict[str, float]


COHORTS: tuple[Cohort, ...] = (
    Cohort(id="binge", name="The Binge Listener",
           weights={"urgency": 0.6, "open_obligations": 0.3, "fairness": 0.1}),
    Cohort(id="mystery", name="The Mystery Purist",
           weights={"fairness": 0.7, "open_obligations": 0.2, "urgency": 0.1}),
    Cohort(id="romance", name="The Romance Listener",
           weights={"emotional_payoff": 0.7, "urgency": 0.2, "fairness": 0.1}),
    Cohort(id="skeptic", name="The Skeptic",
           weights={"consistency": 0.8, "fairness": 0.15, "urgency": 0.05}),
    Cohort(id="night", name="The Late-Night Listener",
           weights={"clarity": 0.5, "emotional_payoff": 0.3, "urgency": 0.2}),
)


class CohortReaction(BaseModel):
    cohort_id: str
    episode: int
    engagement: float
    vote: str
    reaction: str
    citation_ids: list[str] = []


def blind_variants(rows: list[dict], seed: int = 42) -> tuple[list[dict], dict[int, int]]:
    """Strip version labels, shuffle, and assign opaque identifiers.

    Returns a tuple of (blinded_rows, unblind_map) where:
    - blinded_rows: list of dicts with 'variant' and 'id' removed, and opaque
      'blind_id' values added (0, 1, 2, ...). Each has 'variant_blinded: True'.
    - unblind_map: dict mapping blind_id (int) back to original row index.

    This prevents information leakage: the returned rows contain no values that
    correlate with variant origin. Without this, evaluator knowledge of which
    text is rewritten flatters it, turning the comparison into a self-graded essay.
    Shuffling alone is insufficient because field values like 'id' still disclose
    variant when they correlate with insertion order.
    """
    # Create indices to track original positions
    indexed_rows = list(enumerate(rows))

    # Shuffle with seed for determinism
    random.Random(seed).shuffle(indexed_rows)

    # Build blinded rows and mapping
    blinded = []
    unblind_map = {}
    for blind_id, (original_index, row) in enumerate(indexed_rows):
        unblind_map[blind_id] = original_index
        blinded.append({
            **{key: value for key, value in row.items() if key != "variant" and key != "id"},
            "blind_id": blind_id,
            "variant_blinded": True
        })

    return blinded, unblind_map


def divergence_by_episode(reactions: list[dict]) -> dict[int, float]:
    """Spread of cohort engagement per episode. High spread = audience trade-off."""
    grouped: dict[int, list[float]] = defaultdict(list)
    for row in reactions:
        grouped[row["episode"]].append(row["engagement"])
    return {
        episode: pstdev(values) if len(values) > 1 else 0.0
        for episode, values in grouped.items()
    }
