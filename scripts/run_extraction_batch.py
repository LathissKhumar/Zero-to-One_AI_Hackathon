"""Submit one governed ai_query extraction statement for a series."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def submit(*, warehouse: str, catalog: str, schema: str, model: str, series_id: str) -> dict:
    template = (Path(__file__).resolve().parent.parent / "sql" / "extract_graph.sql").read_text()
    statement = template.replace("${catalog}", catalog).replace("${db}", schema).replace("${model}", model)
    payload = {"warehouse_id": warehouse, "statement": statement, "parameters": [{"name": "series_id", "value": series_id}], "wait_timeout": "50s"}
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
    if response.get("status", {}).get("state") not in {"SUCCEEDED", "PENDING", "RUNNING"}:
        raise RuntimeError(json.dumps(response.get("status", {}))[:500])
    return response


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warehouse", required=True)
    parser.add_argument("--catalog", default="writers_room")
    parser.add_argument("--schema", default="canonpulse")
    parser.add_argument("--model", required=True)
    parser.add_argument("--series-id", required=True)
    args = parser.parse_args()
    print(json.dumps(submit(warehouse=args.warehouse, catalog=args.catalog, schema=args.schema, model=args.model, series_id=args.series_id)))


if __name__ == "__main__":
    main()
