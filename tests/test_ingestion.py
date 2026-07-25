from __future__ import annotations

import pytest

from app.ingestion import IngestService, Submission, SubmissionEpisode


def _submission() -> Submission:
    return Submission(
        series_id="demo",
        title="Demo",
        genre="thriller",
        episodes=[
            SubmissionEpisode(episode=1, synopsis="Asha promises to return." , writer_id="writer-a"),
            SubmissionEpisode(episode=2, synopsis="The locket is found.", writer_id="writer-b"),
        ],
    )


def test_submission_validates_unique_ordered_episodes():
    with pytest.raises(ValueError, match="unique and sorted"):
        Submission(
            series_id="demo",
            title="Demo",
            genre="thriller",
            episodes=[
                SubmissionEpisode(episode=2, synopsis="two"),
                SubmissionEpisode(episode=1, synopsis="one"),
            ],
        )


def test_fast_pass_is_queryable_before_deep_extraction():
    service = IngestService()
    job = service.submit(_submission())

    assert job.status == "synopsis_ready"
    assert job.deep_status == "pending"
    assert len(job.series.nodes) == 2
    assert job.series.entries
    assert service.get(job.job_id).series.id == "demo"


def test_deep_pass_promotes_atomically_and_is_idempotent():
    service = IngestService()
    job = service.submit(_submission())

    promoted = service.run_deep(job.job_id)
    repeated = service.run_deep(job.job_id)

    assert promoted.status == "complete"
    assert promoted.deep_status == "complete"
    assert repeated.series.model_dump() == promoted.series.model_dump()


def test_duplicate_submission_is_reused():
    service = IngestService()
    first = service.submit(_submission())
    second = service.submit(_submission())
    assert second.job_id == first.job_id

