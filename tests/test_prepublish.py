from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_pre_publish_check_is_non_mutating_and_cited():
    client = TestClient(create_app())
    candidate = {
        "episode": 221,
        "text": "Asha promises she will return to the ferry, but the old locket is silver.",
    }

    response = client.post("/api/prepublish", json=candidate)

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_episode"] == 221
    assert payload["source"] == "file"
    assert payload["complete"] is True
    assert all(item["citations"] for item in payload["findings"])
    assert client.get("/api/series").json()["total_episodes"] == 220


def test_pre_publish_rejects_a_candidate_inside_the_published_series():
    client = TestClient(create_app())
    response = client.post("/api/prepublish", json={"episode": 220, "text": "A quiet morning."})
    assert response.status_code == 422


def test_pre_publish_check_reports_a_retention_delta():
    client = TestClient(create_app())
    candidate = {
        "episode": 221,
        "text": "Asha promises she will return to the ferry, but the old locket is silver.",
    }
    response = client.post("/api/prepublish", json=candidate)
    assert response.status_code == 200
    payload = response.json()
    assert payload["retention_delta"] is not None
    assert payload["prediction"] is not None
    assert "value" in payload["prediction"]
