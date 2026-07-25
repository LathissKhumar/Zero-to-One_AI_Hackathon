"""Where the app's `Series` comes from: committed JSON, or Unity Catalog.

Two implementations of one seam (`SeriesStore.load() -> Series`) so
`app.main` never has to know which source it is talking to -- everything
downstream of `_series_cached()` is unchanged either way.

The two rules that govern this module:

1. No credentials must still work. `store_from_env` defaults to
   `FileSeriesStore` whenever Databricks is not fully configured, and this
   module makes no network call unless `DatabricksSeriesStore.load()` is
   called with a real (non-injected) transport.
2. Configured-but-broken must fail loudly. `DatabricksSeriesStore` never
   catches a failed statement and falls back to the file -- it raises
   `StatementError`. A demo that quietly serves committed JSON while
   claiming to read the lakehouse is the exact failure mode this module
   exists to prevent.

HTTP is done with `urllib`, matching `app.llm_extractor`, so this module adds
no new dependency. The Databricks SQL Statement Execution API is
asynchronous even for a single small query -- a 220-row series can take tens
of seconds -- so the real transport polls; a fake transport in tests can
skip straight to a terminal response.
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path
from typing import Protocol

from app.narrative_models import Excerpt, LedgerEntry, NarrativeNode, PayoffLink, Series
from app.series_loader import load_series

DEFAULT_CATALOG = "writers_room"
DEFAULT_SCHEMA = "canonpulse"


class SeriesStore(Protocol):
    """Anything that can hand back the demo `Series`. `backend` names the
    source visibly -- surfaced in the `/api/series` response and the
    startup log -- so which store is active is never a guess."""

    backend: str

    def load(self) -> Series: ...


class StatementError(RuntimeError):
    """A Databricks SQL statement did not succeed. Raised, never swallowed --
    a caller that turned this into a fallback to the file would be exactly
    the silent degradation this store exists to rule out."""


class FileSeriesStore:
    """Current behaviour: read the committed demo series from disk."""

    backend = "file"

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    def load(self) -> Series:
        return load_series(self._path)


# A `StatementTransport` runs one SQL statement to completion (submitting it
# and, for the real implementation, polling until it leaves PENDING/RUNNING)
# and returns the final Statement Execution API response body. Tests inject
# a fake that returns a canned terminal response directly, so the suite
# never opens a socket or needs a token.
class StatementTransport(Protocol):
    def __call__(self, statement: str) -> dict: ...


def _http_statement_transport(*, host: str, token: str, warehouse_id: str) -> StatementTransport:
    """The only implementation that touches the network.

    POSTs to `/api/2.0/sql/statements`, then polls
    `GET /api/2.0/sql/statements/{id}` while the state is PENDING or
    RUNNING. Polling is not optional: statements over ~220 rows routinely
    take tens of seconds, well past the 50s the initial POST is willing to
    wait synchronously.
    """
    base = host.rstrip("/")

    def _request(method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            f"{base}{path}",
            data=data,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method=method,
        )
        with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))

    def execute(statement: str) -> dict:
        payload = _request(
            "POST",
            "/api/2.0/sql/statements",
            {"warehouse_id": warehouse_id, "statement": statement, "wait_timeout": "50s"},
        )
        statement_id = payload.get("statement_id")
        while (payload.get("status") or {}).get("state") in ("PENDING", "RUNNING"):
            time.sleep(1)
            payload = _request("GET", f"/api/2.0/sql/statements/{statement_id}")
        return payload

    return execute


def _lit(value: str) -> str:
    """SQL string literal. Doubles embedded single quotes."""
    return "'" + value.replace("'", "''") + "'"


def _as_bool(value: object, default: bool = False) -> bool:
    """The Statement API returns every scalar as a string (nulls as JSON
    null). Booleans come back as the literal strings "true"/"false" -- if
    this ever truthy-cast the string instead of comparing it, "false" would
    become True and an unverified payoff link would start protecting
    contradictions it should not."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def _as_int(value: object) -> int | None:
    return None if value is None else int(value)


def _as_float(value: object) -> float | None:
    return None if value is None else float(value)


def _as_list(value: object) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return json.loads(value)


class DatabricksSeriesStore:
    """Reads `series`, `excerpts`, `narrative_nodes`, `ledger_entries`, and
    `payoff_links` from Unity Catalog and reconstitutes the same `Series`
    model `FileSeriesStore` builds from JSON.

    Five statements, always in this order: series (to learn the series id),
    then the four child tables filtered by it. Each statement is checked for
    `SUCCEEDED` before its rows are used; any other terminal state raises
    `StatementError` immediately; no partial `Series` is ever assembled.
    """

    backend = "databricks"

    def __init__(
        self,
        *,
        catalog: str = DEFAULT_CATALOG,
        schema: str = DEFAULT_SCHEMA,
        host: str | None = None,
        token: str | None = None,
        warehouse_id: str | None = None,
        transport: StatementTransport | None = None,
    ) -> None:
        self._catalog = catalog
        self._schema = schema
        if transport is not None:
            self._transport = transport
        else:
            if not (host and token and warehouse_id):
                raise ValueError(
                    "DatabricksSeriesStore needs host, token and warehouse_id "
                    "unless a transport is injected"
                )
            self._transport = _http_statement_transport(
                host=host, token=token, warehouse_id=warehouse_id
            )

    @property
    def _fq(self) -> str:
        return f"{self._catalog}.{self._schema}"

    def _query(self, statement: str) -> list[list]:
        response = self._transport(statement)
        state = (response.get("status") or {}).get("state")
        if state != "SUCCEEDED":
            detail = json.dumps(response.get("status", {}))[:500]
            raise StatementError(f"statement did not succeed ({state}): {detail}")
        return (response.get("result") or {}).get("data_array") or []

    def load(self) -> Series:
        series_rows = self._query(
            f"SELECT series_id, title, genre, total_episodes, ongoing "
            f"FROM {self._fq}.series LIMIT 1"
        )
        if not series_rows:
            raise StatementError("no row in series table -- has the demo series been loaded?")
        series_id, title, genre, total_episodes, ongoing = series_rows[0]
        where = f"WHERE series_id = {_lit(series_id)}"

        excerpts = [
            Excerpt(id=row[0], episode=_as_int(row[1]), text=row[2])
            for row in self._query(
                f"SELECT excerpt_id, episode, text FROM {self._fq}.excerpts {where}"
            )
        ]

        nodes = [
            NarrativeNode(
                id=row[0],
                episode=_as_int(row[1]),
                perceived_index=_as_int(row[2]),
                true_time=_as_float(row[3]),
                summary=row[4],
                entities=_as_list(row[5]),
                valence=_as_float(row[6]) or 0.0,
                excerpt_id=row[7],
            )
            for row in self._query(
                "SELECT node_id, episode, perceived_index, true_time, summary, "
                f"entities, valence, excerpt_id FROM {self._fq}.narrative_nodes {where}"
            )
        ]

        entries = [
            LedgerEntry(
                id=row[0],
                kind=row[1],
                description=row[2],
                episodes=[int(e) for e in _as_list(row[3])],
                excerpt_ids=_as_list(row[4]),
                urgency=_as_int(row[5]) or 3,
                promise_kind=row[6],
                entities=_as_list(row[7]),
            )
            for row in self._query(
                "SELECT entry_id, kind, description, episodes, excerpt_ids, "
                f"urgency, promise_kind, entities FROM {self._fq}.ledger_entries {where}"
            )
        ]

        payoffs = [
            PayoffLink(
                node_id=row[0],
                target_id=row[1],
                episode=_as_int(row[2]),
                rationale=row[3],
                verified=_as_bool(row[4]),
            )
            for row in self._query(
                "SELECT node_id, target_id, episode, rationale, verified "
                f"FROM {self._fq}.payoff_links {where}"
            )
        ]

        return Series(
            id=series_id,
            title=title,
            genre=genre,
            total_episodes=_as_int(total_episodes),
            ongoing=_as_bool(ongoing, default=True),
            nodes=nodes,
            entries=entries,
            payoffs=payoffs,
            excerpts=excerpts,
        )


def store_from_env(env: dict, default_series_path: Path | str) -> SeriesStore:
    """Select `FileSeriesStore` or `DatabricksSeriesStore` from environment
    configuration. Databricks mode requires host, token, AND warehouse id --
    a partial configuration is treated as unconfigured (file mode) rather
    than guessing, since a half-wired Databricks store would fail in a way
    that looks like a bug in this module instead of an incomplete `.env`.
    """
    host = env.get("DATABRICKS_HOST")
    token = env.get("DATABRICKS_TOKEN")
    warehouse_id = env.get("DATABRICKS_WAREHOUSE_ID")
    if host and token and warehouse_id:
        return DatabricksSeriesStore(
            host=host,
            token=token,
            warehouse_id=warehouse_id,
            catalog=env.get("DATABRICKS_CATALOG", DEFAULT_CATALOG),
            schema=env.get("DATABRICKS_SCHEMA", DEFAULT_SCHEMA),
        )
    return FileSeriesStore(default_series_path)
