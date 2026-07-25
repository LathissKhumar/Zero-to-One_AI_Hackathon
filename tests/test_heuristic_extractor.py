from __future__ import annotations

from app.extraction import ExtractionResult
from app.heuristic_extractor import HeuristicExtractor


def episodes() -> list[dict]:
    """Independent of every CanonPulse manifest, deliberately.

    This fixture must never share a character, object, or beat with
    `data/manifest/last_monsoon.yaml` (or any other manifest added later).
    The whole point of `HeuristicExtractor` is that its rules were written
    without seeing the answer key, so discrimination metrics measure real
    extraction skill rather than agreement between a fixture generator and
    a resolver that were shaped by the same author reading the same
    manifest. If this fixture ever reuses manifest vocabulary, any
    extraction rule it happens to make pass becomes suspect for the same
    reason -- write a new, unrelated scenario instead of nudging this one
    closer to a manifest beat.
    """
    return [
        {"series_id": "s", "episode": 1, "synopsis": "Devika finds a locked toolbox. She swears she will open it before the harvest ends."},
        {"series_id": "s", "episode": 5, "synopsis": "Devika admits she never learned to weld the hull plates."},
        {"series_id": "s", "episode": 40, "synopsis": "Devika welds the hull plates using an emergency torch."},
        {"series_id": "s", "episode": 60, "synopsis": "The toolbox finally opens. It was never locked at all."},
    ]


def test_extraction_conforms_to_the_extractor_protocol():
    result = HeuristicExtractor().extract(episodes())
    assert isinstance(result, ExtractionResult)
    assert result.nodes
    assert result.excerpts


def test_a_node_and_excerpt_exist_for_every_episode():
    result = HeuristicExtractor().extract(episodes())
    assert {node.episode for node in result.nodes} == {1, 5, 40, 60}
    assert {excerpt.episode for excerpt in result.excerpts} == {1, 5, 40, 60}


def test_promise_language_opens_an_obligation():
    result = HeuristicExtractor().extract(episodes())
    promises = [entry for entry in result.entries if entry.kind == "promise"]
    assert promises, "'promises to' should open an obligation"
    assert all(entry.excerpt_ids for entry in promises), "every entry must cite"


def test_extracted_payoff_links_start_unverified():
    """Extraction is untrusted by construction, so an extracted twist resolves
    `broken` until something verifies it. That is the guarantee under test."""
    result = HeuristicExtractor().extract(episodes())
    assert all(link.verified is False for link in result.payoffs)


def test_extraction_is_deterministic():
    first = HeuristicExtractor().extract(episodes())
    second = HeuristicExtractor().extract(episodes())
    assert first.model_dump() == second.model_dump()


def test_empty_input_yields_an_empty_result_without_raising():
    result = HeuristicExtractor().extract([])
    assert result.nodes == [] and result.entries == [] and result.rejected == 0
