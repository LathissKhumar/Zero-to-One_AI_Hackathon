"""Boundary feature extraction: graph state -> model input.

Every feature here answers one question: at the moment the episode ends, how much
does the listener still want? Unpaid obligations are the mechanism -- people
continue a serial because something is owed them, not because the last line was
loud.

Two invariants, both load-bearing:

1. **No prose.** Features are structural only. A rewrite cannot move them by
   sounding better, which is what stops the generator from grading itself.
2. **No lookahead.** Everything is computed as of the boundary. A feature that
   consults later episodes inflates offline scores and collapses in production.
"""

from __future__ import annotations

from statistics import fmean

from app.ledger import GRACE_BY_URGENCY, LedgerResolver
from app.narrative_models import BoundaryFeatures, NarrativeNode, Series


class FeatureExtractor:
    """Builds one :class:`BoundaryFeatures` per episode boundary."""

    def __init__(self, resolver: LedgerResolver | None = None) -> None:
        self._resolver = resolver or LedgerResolver()

    def extract_all(self, series: Series) -> list[BoundaryFeatures]:
        return [
            self.extract(series, episode)
            for episode in range(1, series.total_episodes + 1)
        ]

    def extract(self, series: Series, episode: int) -> BoundaryFeatures:
        """Feature vector at the boundary after ``episode``."""
        resolved = self._resolver.resolve_series(series, as_of=episode)

        # Promises still open at this boundary. A promise paid at Ep 40 is closed
        # at boundary 45 but open at boundary 30, so resolution is re-run per
        # boundary rather than filtered from a single whole-series pass.
        open_entries = [item for item in resolved if item.state == "outstanding"]
        ages = [episode - item.entry.origin_episode for item in open_entries]
        urgencies = [item.entry.urgency for item in open_entries]

        suspended = [item for item in resolved if item.state == "suspended"]
        broken = [item for item in resolved if item.state == "broken"]
        overdue = [item for item in open_entries if item.overdue]
        payoff_distances = self._payoff_distances(series, episode)
        fair_density = self._fair_clue_density(resolved)

        return BoundaryFeatures(
            episode=episode,
            open_obligation_count=len(open_entries),
            mean_urgency=fmean(urgencies) if urgencies else 0.0,
            min_payoff_distance=min(payoff_distances) if payoff_distances else float(episode + 1),
            mean_payoff_distance=fmean(payoff_distances) if payoff_distances else float(episode + 1),
            suspended_edge_density=len(suspended) / episode,
            broken_edge_count=len(broken),
            fair_clue_density=fair_density,
            character_thread_count=self._active_threads(open_entries),
            max_obligation_age=max(ages) if ages else 0,
            mean_obligation_age=fmean(ages) if ages else 0.0,
            overdue_count=len(overdue),
            planting_recency=self._planting_recency(resolved, episode),
            suspended_density=len(suspended) / episode,
            broken_count=len(broken),
            sentiment_velocity=self._sentiment_velocity(series.nodes, episode),
            perceived_time_jump=self._perceived_time_jump(series.nodes, episode),
            active_thread_count=self._active_threads(open_entries),
        )

    @staticmethod
    def _payoff_distances(series: Series, episode: int) -> list[int]:
        """Distance to a scheduled downstream payoff, or the no-schedule sentinel."""
        distances = []
        for entry in series.entries:
            if entry.kind != "promise" or entry.origin_episode > episode:
                continue
            future = [
                link.episode - episode
                for link in series.payoffs
                if link.target_id == entry.id and link.episode == episode
            ]
            distances.append(min(future) if future else episode + 1)
        return distances

    @staticmethod
    def _fair_clue_density(resolved) -> float:
        reveals = [item for item in resolved if item.payoff is not None]
        if not reveals:
            return 0.0
        fair = [item for item in reveals if len(item.citations) >= 2]
        return len(fair) / len(reveals)

    @staticmethod
    def _planting_recency(resolved, episode: int) -> int:
        """Episodes since the most recent plant. A long gap reads as drift."""
        plants = [
            item.entry.origin_episode
            for item in resolved
            if item.entry.origin_episode <= episode
        ]
        return episode - max(plants) if plants else episode

    @staticmethod
    def _sentiment_velocity(nodes: list[NarrativeNode], episode: int) -> float:
        """Change in mean valence across the boundary.

        Uses only the current and previous episode, so it stays causal.
        """
        current = [node.valence for node in nodes if node.episode == episode]
        previous = [node.valence for node in nodes if node.episode == episode - 1]
        if not current or not previous:
            return 0.0
        return fmean(current) - fmean(previous)

    @staticmethod
    def _perceived_time_jump(nodes: list[NarrativeNode], episode: int) -> float:
        """How far story-time moves against presentation order at this boundary.

        The one feature that exists only because two graphs are maintained. A large
        value means the audience was just moved through time -- the structural
        fingerprint of a flashback or a withheld reveal.
        """
        current = [node.true_time for node in nodes if node.episode == episode and node.true_time is not None]
        previous = [node.true_time for node in nodes if node.episode == episode - 1 and node.true_time is not None]
        if not current or not previous:
            return 0.0
        return abs(fmean(current) - fmean(previous))

    @staticmethod
    def _active_threads(open_entries) -> int:
        """Distinct entities carrying an open obligation."""
        entities: set[str] = set()
        for item in open_entries:
            entities.update(item.entry.entities)
        return len(entities)
