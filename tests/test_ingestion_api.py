from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_ingestion_api_returns_202_and_exposes_progress():
    client = TestClient(create_app())
    response = client.post(
        "/api/v2/ingestions",
        json={
            "series_id": "s1",
            "title": "S",
            "genre": "thriller",
            "episodes": [{"episode_number": 1, "text": "one"}],
        },
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    status = client.get(f"/api/v2/ingestions/{job_id}")
    assert status.status_code == 200
    assert status.json()["status"] == "queued"


def test_document_ingest_route_creates_a_submission():
    client = TestClient(create_app())
    payload = {
        "parsed": {
            "document": {
                "elements": [
                    {"id": 0, "type": "section_header", "content": "Episode 1", "bbox": [{"page_id": 0}]},
                    {"id": 1, "type": "text", "content": "Rain covered the station.", "bbox": [{"page_id": 0}]},
                ]
            }
        },
        "source_path": "/Volumes/writers/raw/monsoon.docx",
        "series_id": "monsoon-doc",
        "title": "The Monsoon",
        "genre": "drama",
    }
    response = client.post("/api/ingest/document", json=payload)
    assert response.status_code == 202
    body = response.json()
    assert body["review_required"] is False
    assert body["job"]["series_id"] == "monsoon-doc"


def test_document_ingest_route_reports_review_required():
    client = TestClient(create_app())
    payload = {
        "parsed": {"document": {"elements": [{"id": 1, "type": "text", "content": "A single episode."}]}},
        "source_path": "/Volumes/writers/raw/upload.docx",
        "series_id": "monsoon-doc-2",
        "title": "The Monsoon",
        "genre": "drama",
    }
    response = client.post("/api/ingest/document", json=payload)
    assert response.status_code == 202
    assert response.json()["review_required"] is True


def test_ingestion_series_route_returns_assembled_series():
    client = TestClient(create_app())
    submission = {
        "series_id": "s-series-route",
        "title": "S",
        "genre": "thriller",
        "episodes": [{"episode_number": 1, "text": "Ana promises to return to the ferry."}],
    }
    created = client.post("/api/v2/ingestions", json=submission)
    job_id = created.json()["job_id"]
    client.post(f"/api/v2/ingestions/{job_id}/cancel")
    response = client.get(f"/api/v2/ingestions/{job_id}/series")
    assert response.status_code == 200
    assert response.json()["id"] == "s-series-route"


def test_ingestion_api_rejects_duplicate_episodes():
    client = TestClient(create_app())
    response = client.post(
        "/api/v2/ingestions",
        json={
            "series_id": "s1",
            "title": "S",
            "genre": "thriller",
            "episodes": [
                {"episode_number": 1, "text": "one"},
                {"episode_number": 1, "text": "again"},
            ],
        },
    )
    assert response.status_code == 422
