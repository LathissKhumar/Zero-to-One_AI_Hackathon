"""SeriesStore seam: file-backed (default, offline) vs. Unity Catalog-backed.

Rule 1 -- no credentials must still work: with no Databricks env set,
`store_from_env` must return a `FileSeriesStore` and no test here may touch
the network or a token.

Rule 2 -- configured-but-broken must fail loudly: a `DatabricksSeriesStore`
whose statement fails must raise, never quietly return a partial `Series`
(and never fall back to the file).

`DatabricksSeriesStore` is exercised with a fake transport -- a callable that
returns canned Statement Execution API responses -- so nothing here opens a
socket or needs a token.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.narrative_models import Series
from app.series_loader import load_series
from app.store import (
    DatabricksSeriesStore,
    FileSeriesStore,
    StatementError,
    _http_statement_transport,
    store_from_env,
)

SERIES_PATH = Path("data/series/last_monsoon.json")


def _succeeded(rows: list[list]) -> dict:
    return {"status": {"state": "SUCCEEDED"}, "result": {"data_array": rows}}


def _failed(message: str = "boom") -> dict:
    return {"status": {"state": "FAILED", "error": {"message": message}}}


class FakeTransport:
    """Replays canned Statement API responses in call order, and records the
    statements it was asked to run so tests can assert on them if needed."""

    def __init__(self, responses: list[dict]) -> None:
        self._responses = list(responses)
        self.statements: list[str] = []

    def __call__(self, statement: str) -> dict:
        self.statements.append(statement)
        if not self._responses:
            raise AssertionError("transport called more times than responses were queued")
        return self._responses.pop(0)


# ---------------------------------------------------------------------------
# FileSeriesStore
# ---------------------------------------------------------------------------


def test_file_store_matches_series_loader_directly():
    expected = load_series(SERIES_PATH)
    store = FileSeriesStore(SERIES_PATH)
    assert store.load().model_dump() == expected.model_dump()


def test_file_store_backend_label_is_file():
    assert FileSeriesStore(SERIES_PATH).backend == "file"


# ---------------------------------------------------------------------------
# Store selection from environment
# ---------------------------------------------------------------------------


def test_store_from_env_defaults_to_file_when_unconfigured():
    store = store_from_env({}, default_series_path=SERIES_PATH)
    assert isinstance(store, FileSeriesStore)
    assert store.backend == "file"


def test_store_from_env_ignores_partial_databricks_config():
    # Only host and token set, no warehouse id -- must not half-activate
    # Databricks mode; the app must not guess.
    env = {"DATABRICKS_HOST": "https://example.cloud.databricks.com", "DATABRICKS_TOKEN": "tok"}
    store = store_from_env(env, default_series_path=SERIES_PATH)
    assert isinstance(store, FileSeriesStore)


def test_store_from_env_selects_databricks_when_fully_configured():
    env = {
        "DATABRICKS_HOST": "https://example.cloud.databricks.com",
        "DATABRICKS_TOKEN": "tok",
        "DATABRICKS_WAREHOUSE_ID": "wh123",
        "DATABRICKS_CATALOG": "writers_room",
        "DATABRICKS_SCHEMA": "canonpulse",
    }
    store = store_from_env(env, default_series_path=SERIES_PATH)
    assert isinstance(store, DatabricksSeriesStore)
    assert store.backend == "databricks"
    # Construction alone must not touch the network -- no transport was
    # supplied, and .load() is never called in this test.


def test_store_from_env_accepts_databricks_app_oauth_configuration(monkeypatch):
    monkeypatch.setattr("app.store._app_auth_token", lambda: "short-lived")
    store = store_from_env(
        {
            "DATABRICKS_HOST": "https://example.cloud.databricks.com",
            "DATABRICKS_CLIENT_SECRET": "injected-by-app",
            "DATABRICKS_WAREHOUSE_ID": "wh123",
        },
        default_series_path=SERIES_PATH,
    )
    assert isinstance(store, DatabricksSeriesStore)


# ---------------------------------------------------------------------------
# DatabricksSeriesStore, exercised via a fake transport (no network)
# ---------------------------------------------------------------------------


def _fixture_query_responses() -> list[dict]:
    """Five canned responses, in the order DatabricksSeriesStore.load() must
    issue them: series, excerpts, narrative_nodes, ledger_entries, payoff_links."""
    series_row = [["last-monsoon", "The Last Monsoon", "mystery", "220", "true"]]
    excerpt_rows = [
        ["ex-1", "1", "Rina buries a tin box under the fig tree."],
        ["ex-9", "9", "Rina says she can't ride a bicycle."],
    ]
    node_rows = [
        ["n-1", "1", "1", "0.1", "buries the box", '["Rina"]', "0.2", "ex-1"],
        # true_time is SQL NULL here -- must round-trip to Python None, not 0.0.
        ["n-9", "9", "9", None, "denies riding a bike", '["Rina"]', "-0.4", "ex-9"],
    ]
    entry_rows = [
        ["e-1", "contradiction", "box vs bike claim", "[1, 9]", '["ex-1", "ex-9"]', "4", None, '["Rina"]'],
    ]
    # verified comes back as the literal string "false" -- if the store ever
    # truthy-casts a non-empty string, this would flip to True and the link
    # would wrongly protect a contradiction.
    payoff_rows = [
        ["n-9", "e-1", "9", "explains the scar, not the bike", "false"],
    ]
    return [
        _succeeded(series_row),
        _succeeded(excerpt_rows),
        _succeeded(node_rows),
        _succeeded(entry_rows),
        _succeeded(payoff_rows),
    ]


def test_databricks_store_round_trip_produces_a_valid_series():
    transport = FakeTransport(_fixture_query_responses())
    store = DatabricksSeriesStore(
        catalog="writers_room", schema="canonpulse", transport=transport
    )
    series = store.load()
    assert isinstance(series, Series)
    assert series.id == "last-monsoon"
    assert series.title == "The Last Monsoon"
    assert series.total_episodes == 220
    assert series.ongoing is True
    assert {n.id for n in series.nodes} == {"n-1", "n-9"}
    assert {e.id for e in series.excerpts} == {"ex-1", "ex-9"}
    assert len(series.entries) == 1
    assert series.entries[0].episodes == [1, 9]
    assert len(transport.statements) == 5


def test_databricks_store_true_time_null_survives_as_none():
    transport = FakeTransport(_fixture_query_responses())
    store = DatabricksSeriesStore(catalog="writers_room", schema="canonpulse", transport=transport)
    series = store.load()
    by_id = {n.id: n for n in series.nodes}
    assert by_id["n-1"].true_time == pytest.approx(0.1)
    assert by_id["n-9"].true_time is None


def test_databricks_store_verified_survives_as_a_real_boolean_not_a_truthy_string():
    transport = FakeTransport(_fixture_query_responses())
    store = DatabricksSeriesStore(catalog="writers_room", schema="canonpulse", transport=transport)
    series = store.load()
    assert len(series.payoffs) == 1
    link = series.payoffs[0]
    assert link.verified is False
    assert isinstance(link.verified, bool)


def test_databricks_store_ledger_entry_episodes_is_a_list_of_ints():
    transport = FakeTransport(_fixture_query_responses())
    store = DatabricksSeriesStore(catalog="writers_room", schema="canonpulse", transport=transport)
    series = store.load()
    assert series.entries[0].episodes == [1, 9]
    assert all(isinstance(ep, int) for ep in series.entries[0].episodes)


def test_databricks_store_raises_on_a_failed_statement_instead_of_returning_partial_series():
    responses = [
        _succeeded([["last-monsoon", "The Last Monsoon", "mystery", "220", "true"]]),
        _failed("warehouse unreachable"),
    ]
    transport = FakeTransport(responses)
    store = DatabricksSeriesStore(catalog="writers_room", schema="canonpulse", transport=transport)
    with pytest.raises(StatementError):
        store.load()


def test_databricks_store_never_falls_back_to_file_on_failure():
    """A broken statement must raise, not silently degrade to FileSeriesStore
    -- the whole point of this seam is that Databricks mode fails loudly."""
    transport = FakeTransport([_failed("no warehouse")])
    store = DatabricksSeriesStore(catalog="writers_room", schema="canonpulse", transport=transport)
    with pytest.raises(StatementError):
        store.load()
    # No JSON fallback path exists on this object at all.
    assert not hasattr(store, "_file_fallback")


def test_http_statement_transport_adds_a_scheme_to_a_bare_host(monkeypatch):
    """Databricks Apps inject DATABRICKS_HOST without a scheme (confirmed
    live: 'dbc-....cloud.databricks.com', not 'https://dbc-....'). Without
    normalisation, urllib raises ValueError('unknown url type') before any
    request is even sent -- this crashed the real deployed app's /api/series."""
    captured_urls: list[str] = []

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"statement_id": "s1", "status": {"state": "SUCCEEDED"}, "result": {}}).encode()

    def fake_urlopen(request, timeout=None):
        captured_urls.append(request.full_url)
        return _FakeResponse()

    monkeypatch.setattr("app.store.urllib.request.urlopen", fake_urlopen)

    transport = _http_statement_transport(host="dbc-53cf8438-33aa.cloud.databricks.com", token="tok", warehouse_id="wh1")
    transport("SELECT 1")

    assert captured_urls[0].startswith("https://dbc-53cf8438-33aa.cloud.databricks.com/")


def test_http_statement_transport_does_not_double_prefix_a_host_with_a_scheme(monkeypatch):
    captured_urls: list[str] = []

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"statement_id": "s1", "status": {"state": "SUCCEEDED"}, "result": {}}).encode()

    def fake_urlopen(request, timeout=None):
        captured_urls.append(request.full_url)
        return _FakeResponse()

    monkeypatch.setattr("app.store.urllib.request.urlopen", fake_urlopen)

    transport = _http_statement_transport(host="https://example.cloud.databricks.com", token="tok", warehouse_id="wh1")
    transport("SELECT 1")

    assert captured_urls[0].startswith("https://example.cloud.databricks.com/")
    assert "https://https://" not in captured_urls[0]


def test_no_credential_is_ever_embedded_in_a_query_statement():
    transport = FakeTransport(_fixture_query_responses())
    store = DatabricksSeriesStore(
        catalog="writers_room",
        schema="canonpulse",
        transport=transport,
        token="sk-super-secret-token",
    )
    store.load()
    for statement in transport.statements:
        assert "sk-super-secret-token" not in statement
