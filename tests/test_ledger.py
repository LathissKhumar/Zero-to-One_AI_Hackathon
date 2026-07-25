from __future__ import annotations

from app.ledger import LedgerResolver, LedgerSummary
from app.narrative_models import Excerpt, LedgerEntry, NarrativeNode, PayoffLink, Series


def build_series(
    entries: list[LedgerEntry] | None = None,
    payoffs: list[PayoffLink] | None = None,
    total_episodes: int = 60,
) -> Series:
    """Minimal series with one contradiction and one promise, both unpaid."""
    default_entries = [
        LedgerEntry(
            id="c-1",
            kind="contradiction",
            description="Tara cannot swim in Ep 3 but dives in Ep 20.",
            episodes=[3, 20],
            excerpt_ids=["ex-3", "ex-20"],
            entities=["Tara"],
        ),
        LedgerEntry(
            id="p-1",
            kind="promise",
            description="The cassette must be played when the rain returns.",
            episodes=[1],
            excerpt_ids=["ex-1"],
            urgency=3,
            promise_kind="mystery",
            entities=["Asha"],
        ),
    ]
    return Series(
        id="test-series",
        title="Test Series",
        genre="thriller",
        total_episodes=total_episodes,
        nodes=[
            NarrativeNode(id="n-30", episode=30, perceived_index=30, summary="Reveal", excerpt_id="ex-30"),
        ],
        entries=entries if entries is not None else default_entries,
        payoffs=payoffs or [],
        excerpts=[
            Excerpt(id="ex-1", episode=1, text="PLAY THIS ONLY WHEN THE RAIN RETURNS."),
            Excerpt(id="ex-3", episode=3, text="Tara never learned to swim."),
            Excerpt(id="ex-20", episode=20, text="Tara dives into the channel."),
            Excerpt(id="ex-30", episode=30, text="'I was never in the water. You saw what you needed to see.'"),
        ],
    )


def resolve_one(entry_id: str, series: Series, **kwargs):
    resolved = LedgerResolver(**kwargs).resolve_series(series)
    return next(item for item in resolved if item.entry.id == entry_id)


def test_contradiction_with_verified_downstream_payoff_is_protected():
    series = build_series(
        payoffs=[
            PayoffLink(
                node_id="n-30",
                target_id="c-1",
                episode=30,
                rationale="Reveals the dive was imagined.",
                verified=True,
            )
        ]
    )
    result = resolve_one("c-1", series)
    assert result.state == "suspended"
    assert result.is_protected
    assert not result.is_defect
    assert result.payoff.episode == 30
    assert "Ep 30" in result.reason


def test_unverified_payoff_does_not_protect_with_no_verifier_configured():
    """The default (no-verifier) path must not grant protection on trust alone.

    Without a verifier, and without the link being pre-marked as trusted ground
    truth, a contradiction cannot be suspended purely on an extractor's say-so --
    that would silently suppress a real plot hole, the worst error this system
    can make.
    """
    series = build_series(
        payoffs=[PayoffLink(node_id="n-30", target_id="c-1", episode=30, rationale="unverified claim")]
    )
    result = resolve_one("c-1", series)
    assert result.state == "broken"
    assert result.is_defect
    assert result.payoff is None


def test_approving_verifier_protects_and_marks_the_link_verified():
    series = build_series(
        payoffs=[PayoffLink(node_id="n-30", target_id="c-1", episode=30, rationale="checked out")]
    )
    result = resolve_one("c-1", series, verifier=lambda link, entry: True)
    assert result.state == "suspended"
    assert result.payoff is not None
    assert result.payoff.verified is True


def test_unverified_payoff_still_pays_off_a_promise():
    """Promises are lower stakes: any matching link discharges one, verified or not."""
    series = build_series(
        payoffs=[PayoffLink(node_id="n-30", target_id="p-1", episode=30, rationale="unverified but fine for a promise")]
    )
    assert resolve_one("p-1", series).state == "paid"


def test_contradiction_without_payoff_is_a_defect():
    result = resolve_one("c-1", build_series())
    assert result.state == "broken"
    assert result.is_defect
    assert result.citations, "a defect must cite the conflicting claims"


def test_promise_with_payoff_is_paid():
    series = build_series(
        payoffs=[PayoffLink(node_id="n-30", target_id="p-1", episode=30, rationale="The cassette plays.")]
    )
    assert resolve_one("p-1", series).state == "paid"


def test_promise_within_grace_is_open_but_not_overdue():
    # urgency 3 -> 40-episode grace; planted Ep 1, horizon Ep 30 -> age 29.
    result = resolve_one("p-1", build_series(total_episodes=30))
    assert result.state == "outstanding"
    assert result.overdue is False


def test_promise_past_grace_is_overdue():
    # age 79 exceeds the 40-episode window for urgency 3.
    result = resolve_one("p-1", build_series(total_episodes=80))
    assert result.state == "outstanding"
    assert result.overdue is True
    assert "past" in result.reason


def test_payoff_in_the_same_episode_does_not_protect():
    """Extraction noise: a reveal cannot discharge a claim the audience is still hearing."""
    series = build_series(
        payoffs=[PayoffLink(node_id="n-30", target_id="c-1", episode=20, rationale="same-episode noise")]
    )
    assert resolve_one("c-1", series).state == "broken"


def test_rejected_verifier_leaves_the_contradiction_broken():
    """A hallucinated payoff must never suppress a real defect."""
    series = build_series(
        payoffs=[PayoffLink(node_id="n-30", target_id="c-1", episode=30, rationale="invented")]
    )
    result = resolve_one("c-1", series, verifier=lambda link, entry: False)
    assert result.state == "broken"


def test_as_of_horizon_hides_later_payoffs():
    series = build_series(
        payoffs=[
            PayoffLink(node_id="n-30", target_id="c-1", episode=30, rationale="Late reveal.", verified=True)
        ]
    )
    early = LedgerResolver().resolve_series(series, as_of=25)
    assert next(item for item in early if item.entry.id == "c-1").state == "broken"


def test_summary_headline_separates_baseline_from_real_defects():
    series = build_series(
        payoffs=[PayoffLink(node_id="n-30", target_id="c-1", episode=30, rationale="Reveal.", verified=True)]
    )
    summary = LedgerSummary(LedgerResolver().resolve_series(series))
    headline = summary.headline()
    assert headline["twists_protected"] == 1
    assert headline["real_holes"] == 0
    # The gap between these two numbers is the product.
    assert headline["baseline_flags"] == 1
