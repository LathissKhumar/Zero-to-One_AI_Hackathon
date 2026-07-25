"""Ledger traversal: deciding what is a defect and what is craft.

The single question this module answers, for every discrepancy in a series:

    Did the author mean it?

A contradiction the story later acknowledges is an intentional twist and must be
protected. The same contradiction with nothing downstream is a plot hole. Naive
consistency checkers cannot tell these apart, so they flag both -- which is why
writers ignore them.

Deliberately deterministic. Extraction upstream uses a model; resolution here is
graph traversal, so the same series always yields the same verdict and the result
can be argued with rather than merely trusted.
"""

from __future__ import annotations

from collections.abc import Callable

from app.narrative_models import (
    Excerpt,
    LedgerEntry,
    PayoffLink,
    ResolvedEntry,
    Series,
)

# Episodes an unpaid promise may sit before it reads as abandoned rather than
# simmering. Urgent setups sour fast; slow-burn threads are allowed to breathe.
GRACE_BY_URGENCY: dict[int, int] = {5: 10, 4: 20, 3: 40, 2: 80, 1: 150}

# A payoff must land after the claim it discharges. Same-episode links are
# extraction noise -- a reveal cannot pay off a promise the audience is still
# hearing for the first time.
MIN_PAYOFF_GAP = 1

Verifier = Callable[[PayoffLink, LedgerEntry], bool]


class LedgerResolver:
    """Resolves raw entries into states, with citations for every verdict.

    A ``verifier`` may be supplied to second-guess the extractor's payoff claims.
    Regardless of whether one is supplied, an unverified link never protects a
    contradiction -- that is the single worst error this system can make: it
    silently suppresses a real defect. A link starts life unverified
    (``PayoffLink.verified`` defaults to ``False``); it becomes trusted either by
    being authored as ground truth with ``verified=True`` already set (the demo
    series does this, since its links are hand-authored, not extracted) or by
    passing a ``verifier`` here that approves it at resolve time. Promises are
    lower stakes -- a payoff link discharges a promise (marks it ``paid``)
    whether or not it is verified.
    """

    def __init__(self, verifier: Verifier | None = None) -> None:
        self._verifier = verifier

    def resolve_series(self, series: Series, as_of: int | None = None) -> list[ResolvedEntry]:
        """Resolve every entry as of ``as_of`` (default: the whole series).

        ``as_of`` exists so features can be recomputed at each boundary without
        leaking later episodes into an earlier prediction.
        """
        horizon = as_of if as_of is not None else series.total_episodes
        excerpts = {excerpt.id: excerpt for excerpt in series.excerpts}
        payoffs = self._index_payoffs(series, horizon)
        return [
            self._resolve_entry(entry, payoffs, excerpts, series, horizon)
            for entry in series.entries
            if entry.latest_episode <= horizon
        ]

    def _index_payoffs(self, series: Series, horizon: int) -> dict[str, list[PayoffLink]]:
        index: dict[str, list[PayoffLink]] = {}
        for link in series.payoffs:
            if link.episode <= horizon:
                index.setdefault(link.target_id, []).append(link)
        for links in index.values():
            links.sort(key=lambda link: link.episode)
        return index

    def _resolve_entry(
        self,
        entry: LedgerEntry,
        payoffs: dict[str, list[PayoffLink]],
        excerpts: dict[str, Excerpt],
        series: Series,
        horizon: int,
    ) -> ResolvedEntry:
        payoff = self._find_payoff(entry, payoffs)
        citations = [excerpts[eid] for eid in entry.excerpt_ids if eid in excerpts]

        if payoff is not None:
            payoff_excerpt = self._payoff_excerpt(payoff, series, excerpts)
            if payoff_excerpt is not None:
                citations = [*citations, payoff_excerpt]

        if entry.kind == "contradiction":
            if payoff is not None:
                span = payoff.episode - entry.origin_episode
                return ResolvedEntry(
                    entry=entry,
                    state="suspended",
                    payoff=payoff,
                    citations=citations,
                    reason=(
                        f"Protected: Ep {payoff.episode} pays this off. "
                        f"Planted Ep {entry.origin_episode}. Span of {span} episodes."
                    ),
                )
            return ResolvedEntry(
                entry=entry,
                state="broken",
                citations=citations,
                reason=(
                    f"No episode through {horizon} acknowledges this. "
                    f"Claims at Ep {' and Ep '.join(str(ep) for ep in sorted(entry.episodes))} conflict."
                ),
            )

        # Promise.
        if payoff is not None:
            return ResolvedEntry(
                entry=entry,
                state="paid",
                payoff=payoff,
                citations=citations,
                reason=f"Paid at Ep {payoff.episode}.",
            )

        age = horizon - entry.origin_episode
        grace = GRACE_BY_URGENCY.get(entry.urgency, 40)
        overdue = age > grace
        return ResolvedEntry(
            entry=entry,
            state="outstanding",
            overdue=overdue,
            citations=citations,
            reason=(
                f"Open for {age} episodes since Ep {entry.origin_episode}; "
                f"{'past' if overdue else 'within'} the {grace}-episode window for urgency {entry.urgency}."
            ),
        )

    def _find_payoff(
        self, entry: LedgerEntry, payoffs: dict[str, list[PayoffLink]]
    ) -> PayoffLink | None:
        """Earliest downstream link that discharges ``entry`` and survives verification.

        A contradiction may only be protected by a link that is verified --
        either pre-marked as trusted ground truth, or approved just now by the
        ``verifier``. Without a verifier and without a pre-marked link, an
        extracted payoff for a contradiction is never enough on its own: the
        entry falls through to ``broken`` rather than being silently protected.
        Promises are discharged by any matching link, verified or not.
        """
        for link in payoffs.get(entry.id, []):
            if link.episode - entry.latest_episode < MIN_PAYOFF_GAP:
                continue
            if self._verifier is not None:
                if not self._verifier(link, entry):
                    continue
                link.verified = True
            if entry.kind == "contradiction" and not link.verified:
                continue
            return link
        return None

    @staticmethod
    def _payoff_excerpt(
        payoff: PayoffLink, series: Series, excerpts: dict[str, Excerpt]
    ) -> Excerpt | None:
        for node in series.nodes:
            if node.id == payoff.node_id and node.excerpt_id:
                return excerpts.get(node.excerpt_id)
        return None


class LedgerSummary:
    """Counts behind the comparison screen.

    ``baseline_flags`` is what a checker without the payoff test reports: every
    contradiction, intentional or not. The gap between it and ``broken`` is the
    product.
    """

    def __init__(self, resolved: list[ResolvedEntry]) -> None:
        self._resolved = resolved

    @property
    def broken(self) -> list[ResolvedEntry]:
        return [item for item in self._resolved if item.state == "broken"]

    @property
    def suspended(self) -> list[ResolvedEntry]:
        return [item for item in self._resolved if item.state == "suspended"]

    @property
    def outstanding(self) -> list[ResolvedEntry]:
        return [item for item in self._resolved if item.state == "outstanding"]

    @property
    def overdue(self) -> list[ResolvedEntry]:
        return [item for item in self._resolved if item.overdue]

    @property
    def paid(self) -> list[ResolvedEntry]:
        return [item for item in self._resolved if item.state == "paid"]

    @property
    def baseline_flags(self) -> int:
        return len(self.broken) + len(self.suspended)

    def headline(self) -> dict[str, int]:
        return {
            "baseline_flags": self.baseline_flags,
            "real_holes": len(self.broken),
            "twists_protected": len(self.suspended),
            "overdue_obligations": len(self.overdue),
        }
