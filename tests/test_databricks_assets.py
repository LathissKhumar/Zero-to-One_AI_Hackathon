"""Deployment assets must match the product that actually exists.

These are not style checks. A bundle variable the SQL never reads, or a SQL
placeholder the bundle never defines, fails at deploy time in a workspace --
which is the one place this repo cannot exercise in CI. So the coupling is
pinned here instead.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

BUNDLE = Path("databricks.yml")
SQL_DIR = Path("sql")

# Vocabulary from the superseded A/B narrative-debt product. Its modules were
# deleted; deployment assets that still name it would provision tables the code
# no longer reads.
SUPERSEDED_TERMS = (
    "narrative_debts",
    "story_claims",
    "court_verdicts",
    "audience_cohorts",
    "Audience Court",
    "narrative debt",
)


def _placeholders(text: str) -> set[str]:
    """Every ``${name}`` substitution a SQL file expects."""
    return set(re.findall(r"\$\{(\w+)\}", text))


def test_every_sql_placeholder_is_declared_in_the_bundle():
    """A placeholder with no bundle variable deploys as literal '${db}'."""
    declared = set(yaml.safe_load(BUNDLE.read_text())["variables"])
    # `db` and `schema` name the same thing; the bundle may use either spelling
    # so long as the SQL's placeholder resolves.
    declared |= {"db"} if "schema" in declared else set()

    undeclared: dict[str, set[str]] = {}
    for sql_file in SQL_DIR.glob("*.sql"):
        missing = _placeholders(sql_file.read_text()) - declared
        if missing:
            undeclared[sql_file.name] = missing

    assert not undeclared, f"SQL placeholders with no bundle variable: {undeclared}"


def test_deployment_assets_do_not_reference_the_superseded_product():
    """bootstrap.sql once created story_claims/narrative_debts/court_verdicts.

    Those tables belong to the deleted A/B engine and their `episodes` schema
    contradicts sql/ddl.sql. Deploying both would provision two incompatible
    definitions of the same table name.
    """
    assets = [*SQL_DIR.glob("*.sql"), BUNDLE, Path("app.yaml")]
    assets += list(Path("resources").glob("*.yml"))

    offenders: dict[str, list[str]] = {}
    for asset in assets:
        text = asset.read_text()
        hits = [term for term in SUPERSEDED_TERMS if term in text]
        if hits:
            offenders[str(asset)] = hits

    assert not offenders, f"deployment assets still name the deleted product: {offenders}"


def test_the_schema_ddl_is_the_single_source_of_table_definitions():
    """Exactly one SQL file may CREATE TABLE, or the definitions can drift."""
    creators = [
        sql_file.name
        for sql_file in SQL_DIR.glob("*.sql")
        if "CREATE TABLE" in sql_file.read_text().upper()
    ]
    assert creators == ["ddl.sql"], f"more than one file defines tables: {creators}"


def test_batch_inference_runs_through_ai_query_not_a_vendor_sdk():
    reactions = (SQL_DIR / "cohort_reactions.sql").read_text()
    extraction = (SQL_DIR / "extract_graph.sql").read_text()
    for name, text in (("cohort_reactions", reactions), ("extract_graph", extraction)):
        assert "ai_query" in text, f"{name} does not use ai_query"
    assert "responseFormat" in reactions


def test_document_processing_uses_databricks_document_parser():
    raw = (SQL_DIR / "document_raw.sql").read_text()
    parsed = (SQL_DIR / "document_parse.sql").read_text()
    assert "format => 'binaryFile'" in raw
    assert "ai_parse_document" in parsed
    assert "parsed_document" in parsed


def test_no_credential_is_committed_in_a_deployment_asset():
    for asset in (BUNDLE, Path("app.yaml"), *Path("resources").glob("*.yml")):
        text = asset.read_text()
        assert "OPENAI_API_KEY=" not in text
        assert not re.search(r"dapi[0-9a-f]{32}", text), f"Databricks PAT in {asset}"
