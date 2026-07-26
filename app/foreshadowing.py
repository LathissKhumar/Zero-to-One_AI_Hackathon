"""Reversible micro-foreshadowing proposals; proposals never mutate source."""

from __future__ import annotations

import hashlib

from pydantic import BaseModel, Field

from app.ledger import LedgerResolver
from app.narrative_models import Series


class ForeshadowingProposal(BaseModel):
    proposal_id: str
    obligation_id: str
    insertion_episode: int
    clue_type: str
    text_delta: str
    expected_payoff_relation: str
    confusion_risk: str
    original_excerpt: str
    original_summary: str | None = None


class ForeshadowingEngine:
    def propose(self, source: Series, obligation_id: str, insertion_episode: int, clue_type: str) -> ForeshadowingProposal:
        resolved = {item.entry.id: item for item in LedgerResolver().resolve_series(source, as_of=insertion_episode)}
        item = resolved.get(obligation_id)
        if item is None or item.state != "outstanding":
            raise ValueError("foreshadowing must target an outstanding obligation")
        excerpt = next((excerpt for excerpt in source.excerpts if excerpt.episode == insertion_episode), None)
        node = next((node for node in source.nodes if node.episode == insertion_episode), None)
        if excerpt is None or node is None:
            raise ValueError("insertion episode needs a source excerpt and node")
        delta = f" [{clue_type}: {item.entry.description}]"
        return ForeshadowingProposal(
            proposal_id=hashlib.sha256(f"{source.source_version}:{obligation_id}:{insertion_episode}:{clue_type}".encode()).hexdigest()[:16],
            obligation_id=obligation_id,
            insertion_episode=insertion_episode,
            clue_type=clue_type,
            text_delta=delta,
            expected_payoff_relation=f"supports {obligation_id}",
            confusion_risk="low; inserted as a single bounded clue",
            original_excerpt=excerpt.text,
            original_summary=node.summary,
        )

    def apply(self, source: Series, proposal: ForeshadowingProposal) -> Series:
        changed = source.model_copy(deep=True)
        excerpt = next((item for item in changed.excerpts if item.episode == proposal.insertion_episode), None)
        node = next((item for item in changed.nodes if item.episode == proposal.insertion_episode), None)
        if excerpt is None or node is None:
            raise ValueError("proposal insertion episode is absent")
        excerpt.text += proposal.text_delta
        node.summary += proposal.text_delta
        return changed

    def revert(self, changed: Series, proposal: ForeshadowingProposal) -> Series:
        restored = changed.model_copy(deep=True)
        excerpt = next(item for item in restored.excerpts if item.episode == proposal.insertion_episode)
        node = next(item for item in restored.nodes if item.episode == proposal.insertion_episode)
        excerpt.text = proposal.original_excerpt
        node.summary = proposal.original_summary or node.summary
        return restored

