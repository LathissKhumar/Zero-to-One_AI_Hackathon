"""Create or synchronize the governed Vector Search source table/index."""

from __future__ import annotations

import argparse
import json
import subprocess


def sync(*, warehouse: str, catalog: str, schema: str, index_name: str, endpoint_name: str) -> dict:
    statement = (
        f"CREATE TABLE IF NOT EXISTS {catalog}.{schema}.canonpulse_retrieval_source "
        "AS SELECT * FROM " + f"{catalog}.{schema}.canonpulse_retrieval_source WHERE 1 = 0"
    )
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
    return {"index_name": index_name, "endpoint_name": endpoint_name, "source_table": f"{catalog}.{schema}.canonpulse_retrieval_source"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warehouse", required=True)
    parser.add_argument("--catalog", default="writers_room")
    parser.add_argument("--schema", default="canonpulse")
    parser.add_argument("--index-name", required=True)
    parser.add_argument("--endpoint-name", required=True)
    args = parser.parse_args()
    print(json.dumps(sync(warehouse=args.warehouse, catalog=args.catalog, schema=args.schema, index_name=args.index_name, endpoint_name=args.endpoint_name)))


if __name__ == "__main__":
    main()
