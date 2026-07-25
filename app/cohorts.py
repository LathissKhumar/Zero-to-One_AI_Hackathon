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


def blind_variants(rows: list[dict], seed: int = 42) -> list[dict]:
    """Strip version labels and shuffle before evaluation.

    Without this the evaluator knows which text is the rewrite and flatters it,
    which turns the whole before/after comparison into a self-graded essay.
    """
    blinded = [
        {**{key: value for key, value in row.items() if key != "variant"},
         "variant_blinded": True}
        for row in rows
    ]
    random.Random(seed).shuffle(blinded)
    return blinded


def divergence_by_episode(reactions: list[dict]) -> dict[int, float]:
    """Spread of cohort engagement per episode. High spread = audience trade-off."""
    grouped: dict[int, list[float]] = defaultdict(list)
    for row in reactions:
        grouped[row["episode"]].append(row["engagement"])
    return {
        episode: pstdev(values) if len(values) > 1 else 0.0
        for episode, values in grouped.items()
    }
