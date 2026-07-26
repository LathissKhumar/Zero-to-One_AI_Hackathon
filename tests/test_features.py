from __future__ import annotations

from app.features import FeatureExtractor
from app.feature_schema import FEATURE_ORDER
from app.narrative_models import LedgerEntry, NarrativeNode, PayoffLink
from tests.test_ledger import build_series


def test_features_ignore_everything_after_the_boundary():
    """The no-lookahead invariant, in executable form.

    A feature that consults later episodes inflates offline metrics and collapses
    in production, so this test guards the whole feature module. It isn't enough
    to mutate ``payoffs`` alone: a contradiction whose *first* claim lands at or
    before the boundary but whose *second*, conflicting claim lands after it must
    also be invisible, or the resolver leaks the future into the present the
    moment two claims straddle the horizon.
    """
    series = build_series(total_episodes=60)
    baseline = FeatureExtractor().extract(series, episode=10)

    mutated = series.model_copy(deep=True)
    mutated.payoffs.append(
        PayoffLink(node_id="n-30", target_id="p-1", episode=30, rationale="later payoff")
    )
    # A contradiction planted before the boundary (Ep 5) whose conflicting claim
    # doesn't exist yet at the boundary (Ep 90, far past horizon 10). Only the
    # *latest* claim should gate visibility -- origin_episode alone would let
    # this leak in and move broken_count at boundary 10.
    mutated.entries.append(
        LedgerEntry(
            id="c-future",
            kind="contradiction",
            description="A contradiction whose second claim hasn't happened yet at this boundary.",
            episodes=[5, 90],
            excerpt_ids=[],
            entities=["Nobody"],
        )
    )
    mutated.nodes.append(
        NarrativeNode(
            id="n-90",
            episode=90,
            perceived_index=90,
            summary="A node from far past the boundary.",
            true_time=0.9,
            valence=-0.8,
        )
    )
    after = FeatureExtractor().extract(mutated, episode=10)

    assert after == baseline


def test_open_obligations_are_counted_at_the_boundary():
    features = FeatureExtractor().extract(build_series(total_episodes=60), episode=10)
    assert features.open_obligation_count == 1
    assert features.mean_urgency == 3.0
    assert features.max_obligation_age == 9  # planted Ep 1, boundary Ep 10


def test_paid_obligations_drop_out_of_the_open_count():
    series = build_series(
        payoffs=[PayoffLink(node_id="n-30", target_id="p-1", episode=30, rationale="paid")],
        total_episodes=60,
    )
    assert FeatureExtractor().extract(series, episode=40).open_obligation_count == 0


def test_overdue_count_rises_past_the_grace_window():
    series = build_series(total_episodes=200)
    assert FeatureExtractor().extract(series, episode=20).overdue_count == 0
    assert FeatureExtractor().extract(series, episode=100).overdue_count == 1


def test_feature_vector_excludes_the_episode_index():
    """Episode number is bookkeeping, not signal -- training on it would let the
    model memorise position rather than structure."""
    vector = FeatureExtractor().extract(build_series(), episode=10).to_vector()
    assert "episode" not in vector
    assert all(isinstance(value, float) for value in vector.values())


def test_feature_vector_uses_canonical_payoff_and_clue_names():
    vector = FeatureExtractor().extract(build_series(), episode=10).to_vector()
    assert tuple(vector) == FEATURE_ORDER
    assert "min_payoff_distance" in vector
    assert "mean_payoff_distance" in vector
    assert "fair_clue_density" in vector
