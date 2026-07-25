from pathlib import Path


def test_databricks_assets_are_parameterized_and_use_ai_query():
    bundle = Path("databricks.yml").read_text()
    reactions = Path("sql/cohort_reactions.sql").read_text()

    assert "catalog:" in bundle
    assert "schema:" in bundle
    assert "ai_query" in reactions
    assert "${catalog}" in reactions
    assert "${db}" in reactions
    assert "${model}" in reactions
    assert "responseFormat" in reactions
    assert "OPENAI_API_KEY=" not in bundle
