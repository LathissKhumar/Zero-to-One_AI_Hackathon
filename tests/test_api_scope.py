from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_series_route_rejects_actor_without_series_access():
    client = TestClient(create_app())
    response = client.get("/api/v2/series/secret/version/v1", headers={"X-Actor-Id": "writer-1"})
    assert response.status_code == 403


def test_approval_is_scoped_and_audited():
    client = TestClient(create_app())
    headers = {"X-Actor-Id": "writer-1", "X-Series-Ids": "s1"}
    response = client.post("/api/v2/series/s1/versions/v1/issues/i1/approve", headers=headers)
    assert response.status_code == 200
    assert response.json()["request_id"]
    audit = client.get("/api/v2/series/s1/versions/v1/audit", headers=headers)
    assert audit.json()["events"][0]["issue_id"] == "i1"
