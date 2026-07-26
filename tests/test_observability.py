from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.observability import OperationalEvent, RunContext
from fastapi.testclient import TestClient
from app.main import create_app
from app.observability import EVENT_SINK


def test_event_requires_run_and_request_correlation():
    with pytest.raises(ValueError, match="request_id"):
        OperationalEvent(
            event_name="prediction",
            context=RunContext(
                request_id="", run_id="r1", series_id="s", version_id="v",
                source_version="sv", model_version="m",
            ),
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            latency_ms=1,
            status="ok",
            cost_usd=0,
        )


def test_request_event_links_request_id_and_model_context():
    EVENT_SINK.events.clear()
    response = TestClient(create_app()).get("/api/series", headers={"X-Request-Id": "req-1"})
    assert response.status_code == 200
    event = EVENT_SINK.events[-1]
    assert event.context.request_id == "req-1"
    assert event.context.model_version
