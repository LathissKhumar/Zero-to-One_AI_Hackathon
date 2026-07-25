from __future__ import annotations

from app.extraction import ExtractionResult
from app.heuristic_extractor import HeuristicExtractor


def episodes() -> list[dict]:
    return [
        {"series_id": "s", "episode": 1, "synopsis": "Asha finds a cassette. She promises to play it when the rain returns."},
        {"series_id": "s", "episode": 3, "synopsis": "Tara admits she never learned to swim."},
        {"series_id": "s", "episode": 20, "synopsis": "Tara dives into the black channel water."},
        {"series_id": "s", "episode": 30, "synopsis": "The cassette finally plays. It was never her father's voice."},
    ]


def test_extraction_conforms_to_the_extractor_protocol():
    result = HeuristicExtractor().extract(episodes())
    assert isinstance(result, ExtractionResult)
    assert result.nodes
    assert result.excerpts


def test_a_node_and_excerpt_exist_for_every_episode():
    result = HeuristicExtractor().extract(episodes())
    assert {node.episode for node in result.nodes} == {1, 3, 20, 30}
    assert {excerpt.episode for excerpt in result.excerpts} == {1, 3, 20, 30}


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
