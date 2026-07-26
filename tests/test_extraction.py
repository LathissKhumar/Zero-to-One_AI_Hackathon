from __future__ import annotations

from app.extraction import (
    DatabricksExtractor,
    ExtractionResult,
    FakeExtractor,
    parse_extraction_row,
)


class FakeCursor:
    """Minimal DB-API cursor stand-in. Records the statement/params it was
    called with and hands back pre-seeded rows on fetchall."""

    def __init__(self, rows: list[tuple[str]]):
        self._rows = rows
        self.executed_statement: str | None = None
        self.executed_params: dict | None = None

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def execute(self, statement: str, params: dict | None = None) -> None:
        self.executed_statement = statement
        self.executed_params = params

    def fetchall(self):
        return self._rows


class FakeConnection:
    def __init__(self, rows: list[tuple[str]]):
        self._cursor = FakeCursor(rows)

    def cursor(self):
        return self._cursor


def test_fake_extractor_returns_a_usable_graph():
    result = FakeExtractor().extract([{"episode": 1, "synopsis": "Asha finds a cassette."}])
    assert isinstance(result, ExtractionResult)
    assert result.nodes
    assert result.rejected == 0


def test_malformed_rows_are_rejected_without_killing_the_batch():
    """A partial graph degrades the verdict; a crash loses the whole series."""
    rows = [
        '{"nodes": [{"id": "n-1", "episode": 1, "perceived_index": 1, "summary": "ok"}]}',
        "not json at all",
        '{"nodes": [{"id": "n-2", "episode": 2, "perceived_index": 2, "summary": "ok"}]}',
    ]
    parsed = [parse_extraction_row(row) for row in rows]
    assert sum(1 for item in parsed if item is None) == 1
    assert sum(1 for item in parsed if item is not None) == 2


def test_payoff_links_start_unverified():
    """Protection requires verification; trusting the extractor by default would
    let a hallucinated payoff suppress a real defect."""
    result = FakeExtractor().extract([{"episode": 1, "synopsis": "Asha finds a cassette."}])
    assert all(link.verified is False for link in result.payoffs)


def test_schema_invalid_row_is_rejected_without_killing_the_batch():
    """Valid JSON that fails pydantic validation (e.g. a node missing a
    required field) must not raise -- it should count as rejected, and rows
    after it must still land in the result."""
    rows = [
        # Missing required "summary" -- valid JSON, schema-invalid.
        ('{"nodes": [{"id": "n-1", "episode": 1, "perceived_index": 1}]}',),
        ('{"nodes": [{"id": "n-2", "episode": 2, "perceived_index": 2, "summary": "ok"}]}',),
    ]
    connection = FakeConnection(rows)
    extractor = DatabricksExtractor(connection, catalog="cat", schema="db", model="m")

    result = extractor.extract([{"episode": 1, "series_id": "s1"}])

    assert result.rejected == 1
    assert len(result.nodes) == 1
    assert result.nodes[0].id == "n-2"


def test_extract_with_no_episodes_returns_empty_result_without_querying():
    connection = FakeConnection(rows=[])
    extractor = DatabricksExtractor(connection, catalog="cat", schema="db", model="m")

    result = extractor.extract([])

    assert result == ExtractionResult()
    assert connection._cursor.executed_statement is None


def test_extract_binds_series_id_from_episodes():
    connection = FakeConnection(rows=[])
    extractor = DatabricksExtractor(connection, catalog="cat", schema="db", model="m")

    extractor.extract([{"episode": 1, "series_id": "last-monsoon"}, {"episode": 2, "series_id": "last-monsoon"}])

    assert connection._cursor.executed_params == {"series_id": "last-monsoon"}
    assert ":series_id" in connection._cursor.executed_statement


def test_databricks_extractor_cannot_self_verify_payoff_links():
    connection = FakeConnection([
        ('{"payoffs": [{"node_id": "n-2", "target_id": "c-1", "episode": 2, "rationale": "revealed", "verified": true}]}',),
    ])
    result = DatabricksExtractor(connection, catalog="cat", schema="db", model="m").extract([{"episode": 1, "series_id": "s1"}])
    assert result.payoffs and result.payoffs[0].verified is False
