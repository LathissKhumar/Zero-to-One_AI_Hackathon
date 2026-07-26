"""Parse uploaded documents in a Unity Catalog Volume with ai_parse_document.

This produces governed Bronze and Silver tables. Episode segmentation is kept
in Python (``app.document_ingestion``) because it is CanonPulse product logic,
not generic document parsing.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def execute(warehouse: str, statement: str) -> dict:
    payload = {"warehouse_id": warehouse, "statement": statement, "wait_timeout": "50s"}
    result = subprocess.run(
        ["databricks", "api", "post", "/api/2.0/sql/statements", "--json", json.dumps(payload)],
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip()[:500])
    response = json.loads(result.stdout)
    if response.get("status", {}).get("state") != "SUCCEEDED":
        raise RuntimeError(json.dumps(response.get("status", {}))[:500])
    return response


def run(*, warehouse: str, source_path: str, series_id: str, catalog: str, schema: str) -> None:
    if not source_path.startswith("/Volumes/"):
        raise ValueError("source_path must be a Unity Catalog Volume path under /Volumes/")
    replacements = {
        "${catalog}": catalog,
        "${db}": schema,
        "__SOURCE_PATH__": source_path.replace("'", "''"),
        "__SERIES_ID__": series_id.replace("'", "''"),
    }
    for filename in ("document_raw.sql", "document_parse.sql"):
        statement = (ROOT / "sql" / filename).read_text(encoding="utf-8")
        for token, value in replacements.items():
            statement = statement.replace(token, value if token != "__SOURCE_PATH__" else source_path.replace("'", "''"))
        execute(warehouse, statement)
        print(f"applied {filename}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warehouse", required=True)
    parser.add_argument("--source-path", required=True, help="Unity Catalog Volume path, for example /Volumes/main/raw/series/")
    parser.add_argument("--series-id", required=True)
    parser.add_argument("--catalog", default="writers_room")
    parser.add_argument("--schema", default="canonpulse")
    args = parser.parse_args()
    run(warehouse=args.warehouse, source_path=args.source_path, series_id=args.series_id, catalog=args.catalog, schema=args.schema)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
