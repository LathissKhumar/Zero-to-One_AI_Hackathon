from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_audit_separates_protected_twists_from_real_holes(client):
    payload = client.get("/api/audit").json()
    assert payload["headline"]["baseline_flags"] > payload["headline"]["real_holes"]
    assert payload["headline"]["twists_protected"] > 0


def test_every_surfaced_finding_carries_a_citation(client):
    payload = client.get("/api/audit").json()
    for finding in payload["findings"]:
        assert finding["citations"], f"{finding['entry']['id']} surfaced with no evidence"


def test_discrimination_reports_measured_not_asserted_scores(client):
    report = client.get("/api/discrimination").json()
    assert 0.0 <= report["precision"] <= 1.0
    assert 0.0 <= report["recall"] <= 1.0
    assert report["holes_total"] == 6
    assert report["twists_total"] == 5


def test_root_serves_the_dashboard(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "CanonPulse" in response.text


def test_dashboard_shows_the_baseline_comparison(client):
    body = client.get("/").text
    assert "Baseline checker" in body
    assert "CanonPulse" in body
    assert "Protected" in body
