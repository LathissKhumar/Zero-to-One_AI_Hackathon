"""Apply sql/ddl.sql to a real Unity Catalog schema via the SQL Statement API.

sql/ddl.sql documents itself as parameterisable but nothing in this repo ever
actually ran it against a workspace -- this closes that gap. Splits the file
into individual statements (the Statement Execution API takes one statement
per call) and executes them in order through an authenticated `databricks`
CLI, the same subprocess pattern scripts/build_vector_index.py already uses.

Idempotent: every statement is `CREATE ... IF NOT EXISTS`, so re-running is
a no-op against an already-provisioned schema.

Usage:
    uv run python scripts/apply_ddl.py --warehouse <id> \
        --catalog writers_room --schema canonpulse
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DDL_PATH = REPO_ROOT / "sql" / "ddl.sql"


def _strip_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.split("--", 1)[0]
        lines.append(stripped)
    return "\n".join(lines)


_ALLOW_COLUMN_DEFAULTS = "TBLPROPERTIES ('delta.feature.allowColumnDefaults' = 'supported')"


def _with_column_defaults_enabled(statement: str) -> str:
    """Delta rejects a CREATE TABLE with a column DEFAULT unless this table
    feature is explicitly declared -- ddl.sql predates ever being run against
    a live Delta table, so it never declared it. Appended here rather than in
    ddl.sql itself so the authored DDL stays the single source of truth
    (see tests/test_databricks_assets.py) while the runner makes it actually
    executable."""
    upper = statement.upper()
    if "CREATE TABLE" in upper and " DEFAULT " in upper and "TBLPROPERTIES" not in upper:
        return f"{statement}\n{_ALLOW_COLUMN_DEFAULTS}"
    return statement


def statements(text: str, *, catalog: str, schema: str) -> list[str]:
    substituted = text.replace("${catalog}", catalog).replace("${db}", schema)
    without_comments = _strip_comments(substituted)
    return [
        _with_column_defaults_enabled(chunk.strip())
        for chunk in without_comments.split(";")
        if chunk.strip()
    ]


def run_statement(*, warehouse: str, statement: str, catalog: str, schema: str) -> dict:
    # Each call to this API is its own session -- a bare `USE catalog.schema`
    # statement earlier in the file would not carry context to a later call.
    # Passing catalog/schema explicitly on every statement sets the same
    # default namespace without relying on session continuity.
    payload = {"warehouse_id": warehouse, "statement": statement, "wait_timeout": "50s"}
    if catalog:
        payload["catalog"] = catalog
    if schema:
        payload["schema"] = schema
    result = subprocess.run(
        ["databricks", "api", "post", "/api/2.0/sql/statements", "--json", json.dumps(payload)],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip()[:500])
    response = json.loads(result.stdout)
    state = response.get("status", {}).get("state")
    if state != "SUCCEEDED":
        raise RuntimeError(json.dumps(response.get("status", {}))[:500])
    return response


def apply(*, warehouse: str, catalog: str, schema: str) -> list[str]:
    applied: list[str] = []
    for statement in statements(DDL_PATH.read_text(encoding="utf-8"), catalog=catalog, schema=schema):
        if statement.upper().startswith("USE "):
            # Redundant once catalog/schema are passed per-call below (each API
            # call is its own session, so USE here would not carry forward
            # anyway) -- skipped rather than sent as a no-op.
            continue
        if statement.upper().startswith("CREATE CATALOG"):
            run_statement(warehouse=warehouse, statement=statement, catalog="", schema="")
        elif statement.upper().startswith("CREATE SCHEMA"):
            # The schema this statement creates does not exist yet -- can't be
            # set as the call's own default namespace.
            run_statement(warehouse=warehouse, statement=statement, catalog=catalog, schema="")
        else:
            run_statement(warehouse=warehouse, statement=statement, catalog=catalog, schema=schema)
        applied.append(statement.split("\n", 1)[0][:80])
    return applied


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warehouse", required=True)
    parser.add_argument("--catalog", default="writers_room")
    parser.add_argument("--schema", default="canonpulse")
    args = parser.parse_args()
    applied = apply(warehouse=args.warehouse, catalog=args.catalog, schema=args.schema)
    print(json.dumps({"statements_applied": len(applied), "first": applied[0], "last": applied[-1]}, indent=2))


if __name__ == "__main__":
    main()
