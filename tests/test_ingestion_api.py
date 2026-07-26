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
