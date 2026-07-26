from __future__ import annotations

import time

from app.personas import AgentRunner, Persona, run_writers_room
from tests.test_variants import _series


def test_writers_room_records_timeout_and_disagreement():
    def handler(persona, graph, budget):
        if persona.id == "slow":
            time.sleep(0.05)
        return {
            "persona_id": persona.id,
            "issue_ids": ("hole",),
            "confidence": 0.5,
            "reason_codes": ("review",),
            "latency_ms": 1.0,
            "timed_out": False,
        }

    personas = [Persona(id="slow", name="Slow", focus="timing"), Persona(id="other", name="Other", focus="timing")]
    result = run_writers_room(_series(), personas, runner=AgentRunner(handler), timeout_s=0.01)
    assert result.timeouts == ["slow"]
    assert result.disagreements[0].issue_id == "hole"

