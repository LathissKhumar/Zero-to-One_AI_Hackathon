from __future__ import annotations

from app.databricks_config import databricks_model_config


def test_databricks_model_config_is_none_without_host(monkeypatch):
    monkeypatch.delenv("DATABRICKS_HOST", raising=False)
    monkeypatch.delenv("SERVING_MODEL_ENDPOINT", raising=False)
    assert databricks_model_config(token_provider=lambda: "unused") is None


def test_databricks_model_config_is_none_without_serving_endpoint(monkeypatch):
    monkeypatch.setenv("DATABRICKS_HOST", "https://dbc-example.cloud.databricks.com")
    monkeypatch.delenv("SERVING_MODEL_ENDPOINT", raising=False)
    assert databricks_model_config(token_provider=lambda: "unused") is None


def test_databricks_model_config_builds_invocation_endpoint(monkeypatch):
    monkeypatch.setenv("DATABRICKS_HOST", "https://dbc-example.cloud.databricks.com")
    monkeypatch.setenv("SERVING_MODEL_ENDPOINT", "databricks-gpt-oss-20b")
    config = databricks_model_config(token_provider=lambda: "sk-fake-token")
    assert config is not None
    assert config.endpoint == "https://dbc-example.cloud.databricks.com/serving-endpoints/databricks-gpt-oss-20b/invocations"
    assert config.token == "sk-fake-token"
    assert config.model == "databricks-gpt-oss-20b"


def test_databricks_model_config_propagates_token_provider_failure(monkeypatch):
    monkeypatch.setenv("DATABRICKS_HOST", "https://dbc-example.cloud.databricks.com")
    monkeypatch.setenv("SERVING_MODEL_ENDPOINT", "databricks-gpt-oss-20b")

    def failing_provider() -> str:
        raise RuntimeError("no Databricks auth available")

    assert databricks_model_config(token_provider=failing_provider) is None
