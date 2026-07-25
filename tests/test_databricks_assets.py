from pathlib import Path


def test_databricks_assets_are_parameterized_and_use_ai_query():
    bundle = Path("databricks.yml").read_text()
    court = Path("sql/audience_court.sql").read_text()

    assert "catalog:" in bundle
    assert "schema:" in bundle
    assert "ai_query" in court
    assert "${var.catalog}.${var.schema}" in court
    assert "responseFormat" in court
    assert "OPENAI_API_KEY=" not in bundle
