from __future__ import annotations

import pytest

from app.ingestion_models import (
    EpisodeInput,
    SubmissionInput,
    parse_submission_json,
    parse_submission_ndjson,
)
from app.ingestion_repository import InMemorySubmissionRepository
from app.ingestion import IngestionCoordinator


def test_ndjson_parser_rejects_duplicate_episode_numbers():
    raw = b'{"episode_number": 1, "text": "a"}\n{"episode_number": 1, "text": "b"}\n'
    with pytest.raises(ValueError, match="duplicate episode_number"):
        parse_submission_ndjson(raw.splitlines())


def test_json_parser_normalizes_episode_order():
    result = parse_submission_json(
        b'{"series_id":"s1","title":"S","genre":"thriller","episodes":['
        b'{"episode_number":2,"text":"b"},{"episode_number":1,"text":"a"}]}'
    )
    assert [episode.episode_number for episode in result.episodes] == [1, 2]


def test_repository_is_idempotent_for_same_source_hash():
    repository = InMemorySubmissionRepository()
    submission = SubmissionInput(
        series_id="s1",
        title="S",
        genre="thriller",
        episodes=[EpisodeInput(episode_number=1, text="one")],
    )
    first = repository.create_submission(submission, source_hash="abc")
    second = repository.create_submission(submission, source_hash="abc")
    assert first.job_id == second.job_id
    assert len(repository.list_work_items(first.job_id, "fast")) == 1


class _Extractor:
    def __init__(self, failing_episode_numbers: set[int] | None = None):
        self.failing_episode_numbers = failing_episode_numbers or set()

    def extract_fast(self, episode: EpisodeInput) -> None:
        return None

    def extract_deep(self, episode: EpisodeInput) -> None:
        if episode.episode_number in self.failing_episode_numbers:
            raise TimeoutError("temporary extraction failure")


def test_deep_retry_only_reprocesses_failed_items():
    submission = SubmissionInput(
        series_id="s1",
        title="S",
        genre="thriller",
        episodes=[EpisodeInput(episode_number=n, text=str(n)) for n in range(1, 4)],
    )
    extractor = _Extractor({2})
    coordinator = IngestionCoordinator(
        repository=InMemorySubmissionRepository(), extractor=extractor
    )
    job = coordinator.submit(submission)
    coordinator.run_fast(job.job_id)
    failed = coordinator.run_deep(job.job_id)
    assert failed.failed_episodes == [2]
    extractor.failing_episode_numbers.clear()
    complete = coordinator.retry(job.job_id)
    assert complete.completed_episodes == 3
    assert complete.reprocessed_episodes == [2]
