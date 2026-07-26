from __future__ import annotations

import os

from app.llm_config import openai_config


def test_openai_config_is_none_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert openai_config() is None


def test_openai_config_reads_key_and_defaults_model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    config = openai_config()
    assert config is not None
    assert config.token == "sk-test-123"
    assert config.model == "gpt-4o-mini"
    assert config.endpoint == "https://api.openai.com/v1/chat/completions"


def test_openai_config_honours_model_override(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    config = openai_config()
    assert config.model == "gpt-4o"
