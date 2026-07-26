from app.document_ingestion import normalize_parsed_document
from app.extraction import ExtractionResult, attach_provenance
from app.extraction_models import ExtractionContext
from app.narrative_models import Excerpt


def test_databricks_document_output_becomes_cited_episode_input():
    parsed = {
        "document": {
            "elements": [
                {"id": 0, "type": "section_header", "content": "Episode 1", "bbox": [{"page_id": 0}]},
                {"id": 1, "type": "text", "content": "Rain covered the station.", "bbox": [{"page_id": 0}]},
                {"id": 2, "type": "section_header", "content": "Episode 2", "bbox": [{"page_id": 2}]},
                {"id": 3, "type": "text", "content": "The lantern went dark.", "bbox": [{"page_id": 2}]},
            ]
        }
    }

    result = normalize_parsed_document(
        parsed,
        source_path="/Volumes/writers/raw/monsoon.docx",
        series_id="monsoon",
        title="The Monsoon",
        genre="drama",
    )

    assert result.review_required is False
    assert [episode.episode_number for episode in result.submission.episodes] == [1, 2]
    assert result.submission.episodes[0].source_pages == [1]
    assert result.submission.episodes[1].source_pages == [3]
    assert result.submission.episodes[0].source_element_ids == [1]


def test_document_without_episode_signal_is_review_required():
    result = normalize_parsed_document(
        {"document": {"elements": [{"id": 1, "type": "text", "content": "A single episode."}]}},
        source_path="/Volumes/writers/raw/upload.docx",
        series_id="monsoon",
        title="The Monsoon",
        genre="drama",
    )

    assert result.review_required is True
    assert result.warnings


def test_filename_can_supply_episode_number_for_one_file_per_episode():
    result = normalize_parsed_document(
        {"document": {"elements": [{"id": 1, "type": "text", "content": "Episode body."}]}},
        source_path="/Volumes/writers/raw/episode-07.pdf",
        series_id="monsoon",
        title="The Monsoon",
        genre="drama",
    )

    assert result.submission.episodes[0].episode_number == 7
    assert result.review_required is False


def test_extraction_citation_carries_document_location():
    result = attach_provenance(
        ExtractionResult(excerpts=[Excerpt(id="ex-7", episode=7, text="Episode body.")]),
        [{"episode": 7, "body": "Episode body.", "source_path": "/Volumes/raw/episode-07.pdf", "source_pages": [3], "source_element_ids": [11]}],
        ExtractionContext(series_id="monsoon", version_id="v1", source_hash="hash", model_name="model", prompt_version="p1"),
    )

    assert result.citations[0].source_path == "/Volumes/raw/episode-07.pdf"
    assert result.citations[0].source_pages == [3]
    assert result.citations[0].source_element_ids == [11]
