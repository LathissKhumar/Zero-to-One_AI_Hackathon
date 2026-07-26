from __future__ import annotations

import json

from app.llm_agents import LLMPersonaHandler
from app.personas import PERSONAS
from tests.test_variants import _series


def test_llm_persona_handler_returns_no_issues_when_nothing_open():
    def fake_transport(*, endpoint, token, model, prompt):
        raise AssertionError("must not call the model when there is nothing open")

    handler = LLMPersonaHandler(endpoint="https://api.openai.com/v1/chat/completions", token="sk-test", model="gpt-4o-mini", transport=fake_transport)
    series = _series().model_copy(update={"entries": []})
    result = handler(PERSONAS[0], series, budget=512)
    assert result["persona_id"] == "director"
    assert result["timed_out"] is False
    assert result["reason_codes"] == ("no_open_obligations",)


def test_llm_persona_handler_parses_model_json_into_annotation_fields():
    calls = []

    def fake_transport(*, endpoint, token, model, prompt):
        calls.append(prompt)
        return json.dumps({"issue_ids": ["hole"], "confidence": 0.83, "reason_codes": ["fairness_risk"]})

    handler = LLMPersonaHandler(endpoint="https://api.openai.com/v1/chat/completions", token="sk-test", model="gpt-4o-mini", transport=fake_transport)
    series = _series()
    result = handler(PERSONAS[2], series, budget=512)

    assert result["confidence"] == 0.83
    assert result["reason_codes"] == ("fairness_risk",)
    assert result["persona_id"] == "critic"
    assert len(calls) == 1
    assert "Critic" in calls[0] or "cliche" in calls[0].lower()


def test_llm_persona_handler_falls_back_when_model_returns_malformed_json():
    def fake_transport(*, endpoint, token, model, prompt):
        return "not json"

    handler = LLMPersonaHandler(endpoint="https://api.openai.com/v1/chat/completions", token="sk-test", model="gpt-4o-mini", transport=fake_transport)
    series = _series()
    result = handler(PERSONAS[1], series, budget=512)

    assert result["confidence"] == 0.0
    assert result["reason_codes"] == ("malformed_model_output",)
