"""Surgical repair and the attribution that justifies it.

Two rules keep this from becoming generic LLM rewriting:

1. Every edit must name the ledger obligation it discharges. An edit that cannot
   is dropped -- that constraint alone removes most of what a model volunteers.
2. Movement in the prediction is decomposed per edit, and whatever cannot be
   attributed is reported rather than absorbed.
"""

from __future__ import annotations

from pydantic import BaseModel, field_validator

from app.narrative_models import BoundaryFeatures
from app.predictor import FEATURE_ORDER

# Features that count actual failures or unresolved gaps rather than ambiguous
# engagement signal. By construction an increase in any of these is never an
# improvement -- there is no reading of "more broken promises" or "an older
# unpaid debt" as a repair. Features outside this set (e.g. open_obligation_count)
# are deliberately excluded: the trained model treats "something is still owed"
# as a live-interest signal, not a defect, so its direction is not asserted here.
_WORSENS_IF_INCREASED: frozenset[str] = frozenset(
    {
        "broken_edge_count", "min_payoff_distance", "mean_payoff_distance",
        "planting_recency", "fair_clue_density",
    }
)

_FEATURE_ALIASES = {
    "broken_count": "broken_edge_count",
    "max_obligation_age": "min_payoff_distance",
    "mean_obligation_age": "mean_payoff_distance",
    "suspended_density": "suspended_edge_density",
    "active_thread_count": "character_thread_count",
}


class EditAttribution(BaseModel):
    hunk: str
    obligation_id: str
    feature_moved: str
    delta: float

    @field_validator("obligation_id")
    @classmethod
    def _must_target_an_obligation(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("every edit must discharge a named ledger obligation")
        return value

    @field_validator("feature_moved")
    @classmethod
    def _must_name_a_real_feature(cls, value: str) -> str:
        value = _FEATURE_ALIASES.get(value, value)
        if value not in FEATURE_ORDER:
            raise ValueError(
                f"'{value}' is not a recognised feature -- the model was never "
                f"trained on it, so movement cannot be attributed to it"
            )
        return value


class RewriteReport(BaseModel):
    total_delta: float
    attributed_delta: float
    unattributed: float
    edits: list[EditAttribution]
    features_before: BoundaryFeatures
    features_after: BoundaryFeatures


def attribute_delta(
    before: BoundaryFeatures,
    after: BoundaryFeatures,
    edits: list[EditAttribution],
    total_delta: float,
) -> RewriteReport:
    """Attribute ``total_delta`` to the caller's named edits.

    Every edit is validated against the actual feature movement it claims
    credit for -- naming a feature is not enough; the feature has to have
    moved, and for features that are unambiguously bad when they increase
    (see ``_WORSENS_IF_INCREASED``), the claimed delta's sign has to agree
    with which way it actually moved. Both failures are rejected (raised as
    ``ValueError``, surfaced by the API as 422) rather than flagged and
    passed through, because a fabricated attribution reaching the UI is
    exactly the false claim this product exists to prevent.
    """
    before_vector = before.to_vector()
    after_vector = after.to_vector()
    for edit in edits:
        diff = after_vector[edit.feature_moved] - before_vector[edit.feature_moved]
        if diff == 0:
            raise ValueError(
                f"edit claims to move '{edit.feature_moved}' but it did not move "
                f"between episode {before.episode} and episode {after.episode}"
            )
        if (
            edit.feature_moved in _WORSENS_IF_INCREASED
            and edit.delta != 0
            and (diff > 0) == (edit.delta > 0)
        ):
            raise ValueError(
                f"'{edit.feature_moved}' got worse ({before_vector[edit.feature_moved]} -> "
                f"{after_vector[edit.feature_moved]}) but the edit claims a delta of "
                f"{edit.delta}, as if it were a repair"
            )

    attributed = sum(edit.delta for edit in edits)
    return RewriteReport(
        total_delta=total_delta,
        attributed_delta=attributed,
        unattributed=total_delta - attributed,
        edits=edits,
        features_before=before,
        features_after=after,
    )
