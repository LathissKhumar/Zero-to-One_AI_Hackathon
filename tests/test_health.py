from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_liveness_returns_200_without_dependencies():
    response = TestClient(create_app()).get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_readiness_reports_dependency_names():
    response = TestClient(create_app()).get("/health/ready")
    assert response.status_code in {200, 503}
    assert {"store", "model", "retrieval"}.issubset(response.json()["checks"])
