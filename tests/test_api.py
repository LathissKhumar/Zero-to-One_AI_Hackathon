from fastapi.testclient import TestClient

from app.main import create_app


def test_compare_endpoint_returns_a_cited_court_verdict():
    client = TestClient(create_app())

    response = client.post("/api/compare", json={"left_slug": "shock-default", "right_slug": "earned-storm"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["winner_slug"] == "earned-storm"
    assert len(payload["court"]) == 5
    assert payload["court"][0]["citation_ids"]


def test_compare_endpoint_rejects_unknown_endings():
    client = TestClient(create_app())

    response = client.post("/api/compare", json={"left_slug": "missing", "right_slug": "earned-storm"})

    assert response.status_code == 422


def test_root_serves_the_canonpulse_dashboard():
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "Narrative Debt Engine" in response.text
    assert "Audience Court" in response.text
