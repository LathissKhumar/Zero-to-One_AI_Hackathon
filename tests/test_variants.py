from __future__ import annotations

import pytest

from app.foreshadowing import ForeshadowingEngine
from app.narrative_models import Excerpt, LedgerEntry, NarrativeNode, Series
from app.personas import PERSONAS, WritersRoom
from app.scrambler import Scrambler
from app.variants import RepairEngine
from app.corpus import normalize_within_book
from app.predictor import ContinuationPredictor
from app.training_corpus import generate_synthetic_corpus


def _series() -> Series:
    return Series(
        id="s",
        title="S",
        genre="thriller",
        total_episodes=3,
        ongoing=True,
        nodes=[
            NarrativeNode(id="n1", episode=1, perceived_index=1, true_time=0.0, summary="Asha finds the key.", entities=["Asha"], excerpt_id="x1"),
            NarrativeNode(id="n2", episode=2, perceived_index=2, true_time=0.5, summary="Asha loses the key.", entities=["Asha"], excerpt_id="x2"),
        ],
        entries=[LedgerEntry(id="hole", kind="contradiction", description="The key is both lost and found.", episodes=[1, 2], entities=["Asha"], excerpt_ids=["x1", "x2"]), LedgerEntry(id="promise", kind="promise", description="Asha will return.", episodes=[1], urgency=4, entities=["Asha"], excerpt_ids=["x1"])],
        excerpts=[Excerpt(id="x1", episode=1, text="Asha finds the key."), Excerpt(id="x2", episode=2, text="Asha loses the key.")],
    )


def test_repair_changes_only_named_node_and_does_not_mutate_source():
    source = _series()
    variant = RepairEngine().repair(source, "hole", "n2", "Asha finds the key in the drawer.")
    assert variant.discharged_entry_ids == ["hole"]
    assert source.nodes[1].summary == "Asha loses the key."
    assert variant.series.nodes[0].summary == source.nodes[0].summary
    assert variant.series.nodes[1].summary != source.nodes[1].summary


def test_variant_score_uses_the_same_frozen_predictor():
    source = _series()
    variant = RepairEngine().repair(source, "hole", "n2", "Asha finds the key in the drawer.")
    predictor = ContinuationPredictor()
    predictor.train(normalize_within_book(generate_synthetic_corpus(n_books=8, chapters_per_book=30)))
    score = predictor.score_variant(source, variant.series, 3)
    assert score.model_version == score.original.model_version == score.variant.model_version
    assert score.delta == pytest.approx(score.variant.value - score.original.value)


def test_scrambler_preserves_true_graph_and_rejects_invalid_order():
    source = _series()
    variant = Scrambler().scramble(source, [2, 1])
    assert variant.true_graph_hash == Scrambler.graph_hash(source)
    assert [node.perceived_index for node in variant.series.nodes] == [2, 1]
    with pytest.raises(ValueError, match="permutation"):
        Scrambler().scramble(source, [1, 1])


def test_foreshadowing_is_reversible_and_targets_an_open_obligation():
    source = _series()
    proposal = ForeshadowingEngine().propose(source, "promise", 2, "object_echo")
    assert proposal.obligation_id == "promise"
    changed = ForeshadowingEngine().apply(source, proposal)
    restored = ForeshadowingEngine().revert(changed, proposal)
    assert restored.model_dump() == source.model_dump()


def test_writers_room_returns_five_citation_backed_structured_annotations():
    annotations = WritersRoom().review(_series(), horizon=2)
    assert {annotation.persona_id for annotation in annotations} == {persona.id for persona in PERSONAS}
    assert all(annotation.citation_ids for annotation in annotations)
    assert all(annotation.target_id for annotation in annotations)
