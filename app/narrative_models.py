"""Domain types for the dual-layer narrative graph and the obligation ledger.

Two graphs over the same nodes:

* ``G_true``      -- chronological story-time. When events actually happen.
* ``G_perceived`` -- presentation order. When the listener learns of them.

A node's position differs between the two whenever the series uses a flashback,
an unreliable narrator, or a withheld reveal. That divergence is signal, not noise:
it is what separates an intentional twist from an accidental contradiction.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

EntryKind = Literal["contradiction", "promise"]

# Ledger states. A contradiction resolves to suspended or broken; a promise to
# paid or outstanding. No entry is ever both.
LedgerState = Literal["suspended", "broken", "paid", "outstanding"]

PromiseKind = Literal["mystery", "causal", "relationship", "emotional", "genre"]


class Excerpt(BaseModel):
    """A citation anchor. Every ledger claim must point at one of these."""

    id: str
    episode: int
    text: str


class NarrativeNode(BaseModel):
    """One extracted story event.

    ``perceived_index`` is the episode the audience hears it in. ``true_time`` is
    its position in chronological story-time, normalised to [0, 1]; ``None`` means
    the extractor could not place it, which is itself common and handled.
    """

    id: str
    episode: int
    perceived_index: int
    true_time: float | None = None
    summary: str
    entities: list[str] = Field(default_factory=list)
    valence: float = Field(default=0.0, ge=-1.0, le=1.0)
    excerpt_id: str | None = None

    @property
    def is_time_displaced(self) -> bool:
        return self.true_time is not None


class PayoffLink(BaseModel):
    """Extractor's claim that ``node_id`` discharges ``target_id``.

    Claims are not trusted on sight -- ``verified`` is set by the resolver, which
    may consult a verifier before honouring the link. An unverified link never
    protects a contradiction.
    """

    node_id: str
    target_id: str
    episode: int
    rationale: str
    verified: bool = False


class LedgerEntry(BaseModel):
    """A contradiction or an unpaid promise, before resolution.

    ``episodes`` holds the episode(s) the entry arises from: two for a
    contradiction (the conflicting claims), one for a promise (where it was planted).
    """

    id: str
    kind: EntryKind
    description: str
    episodes: list[int]
    excerpt_ids: list[str] = Field(default_factory=list)
    urgency: int = Field(default=3, ge=1, le=5)
    promise_kind: PromiseKind | None = None
    entities: list[str] = Field(default_factory=list)

    @property
    def origin_episode(self) -> int:
        return min(self.episodes)

    @property
    def latest_episode(self) -> int:
        return max(self.episodes)


class ResolvedEntry(BaseModel):
    """A ledger entry after traversal, with its state and the evidence for it."""

    entry: LedgerEntry
    state: LedgerState
    overdue: bool = False
    payoff: PayoffLink | None = None
    citations: list[Excerpt] = Field(default_factory=list)
    reason: str = ""

    @property
    def is_protected(self) -> bool:
        """Suspended entries are intentional craft. Never flag them as defects."""
        return self.state == "suspended"

    @property
    def is_defect(self) -> bool:
        return self.state == "broken"


class Series(BaseModel):
    """A writer's full submission. Up to ~300 episodes."""

    id: str
    title: str
    genre: str
    total_episodes: int
    ongoing: bool = True
    nodes: list[NarrativeNode] = Field(default_factory=list)
    entries: list[LedgerEntry] = Field(default_factory=list)
    payoffs: list[PayoffLink] = Field(default_factory=list)
    excerpts: list[Excerpt] = Field(default_factory=list)


class BoundaryFeatures(BaseModel):
    """Feature vector at the boundary after ``episode``.

    Consumed by the continuation regressor. Contains no prose -- by construction a
    rewrite cannot improve this vector by sounding better, only by changing
    structure. That property is what keeps the predictor from grading its own
    author, so nothing derived from raw text may be added here.

    Every field is computable from information available at or before ``episode``.
    Adding a feature that peeks past the boundary silently inflates offline metrics.
    """

    episode: int
    open_obligation_count: int = 0
    mean_urgency: float = 0.0
    max_obligation_age: int = 0
    mean_obligation_age: float = 0.0
    overdue_count: int = 0
    planting_recency: int = 0
    suspended_density: float = 0.0
    broken_count: int = 0
    fair_clue_density: float = 0.0
    sentiment_velocity: float = 0.0
    perceived_time_jump: float = 0.0
    active_thread_count: int = 0

    def to_vector(self) -> dict[str, float]:
        """Ordered mapping for the model. Key order is the training contract."""
        return {
            name: float(getattr(self, name))
            for name in self.model_fields
            if name != "episode"
        }
