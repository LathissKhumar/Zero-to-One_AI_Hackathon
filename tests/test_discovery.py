from fastapi.testclient import TestClient

from app.main import create_app


def test_mood_discovery_explains_its_match():
    client = TestClient(create_app())

    response = client.get("/api/discover", params={"q": "rainy Sunday after heartbreak"})

    assert response.status_code == 200
    assert response.json()[0]["title"] == "After the Rain"
    assert "why" in response.json()[0]
