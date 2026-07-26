"""Persist a materialized Databricks graph-response table into the ledger."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.narrative_models import Excerpt, LedgerEntry, NarrativeNode, PayoffLink  # noqa: E402
from scripts.promote_document_series import Warehouse, extraction_object, response_rows, sql_array, sql_str  # noqa: E402


def persist(*, warehouse: Warehouse, catalog: str, schema: str, series_id: str, response_table: str, model: str) -> dict:
    fq = f"{catalog}.{schema}"
    rows = response_rows(warehouse.execute(f"SELECT episode, extraction FROM {response_table}"))
    if not rows:
        raise RuntimeError(f"no graph response rows in {response_table}")

    submission = response_rows(
        warehouse.execute(
            f"SELECT version_id, source_hash FROM {fq}.canonpulse_submission WHERE series_id = :series_id",
            [{"name": "series_id", "value": series_id}],
        )
    )
    if not submission:
        raise RuntimeError(f"no submission metadata for {series_id}")
    version_id = str(submission[0]["version_id"])
    source_hash = str(submission[0]["source_hash"])
    run_id = f"extract-{uuid.uuid4().hex[:16]}"

    nodes: list[NarrativeNode] = []
    entries: list[LedgerEntry] = []
    payoffs: list[PayoffLink] = []
    excerpts: list[Excerpt] = []
    rejected = 0
    for row in rows:
        parsed = extraction_object(row.get("extraction"))
        if parsed is None:
            rejected += 1
            continue
        try:
            nodes.extend(NarrativeNode.model_validate(item) for item in parsed.get("nodes", []))
            entries.extend(LedgerEntry.model_validate(item) for item in parsed.get("entries", []))
            payoffs.extend(PayoffLink.model_validate({**item, "verified": False}) for item in parsed.get("payoffs", []))
            excerpts.extend(Excerpt.model_validate(item) for item in parsed.get("excerpts", []))
        except Exception:  # noqa: BLE001 - preserve row-level rejection semantics
            rejected += 1

    for table in ("narrative_nodes", "excerpts", "ledger_entries", "payoff_links"):
        warehouse.execute(f"DELETE FROM {fq}.{table} WHERE series_id = :series_id", [{"name": "series_id", "value": series_id}])
    warehouse.execute(f"DELETE FROM {fq}.canonpulse_extraction_run WHERE run_id = :run_id", [{"name": "run_id", "value": run_id}])
    warehouse.execute(
        f"INSERT INTO {fq}.canonpulse_extraction_run (run_id, series_id, version_id, source_hash, model_name, prompt_version, started_at, finished_at, latency_ms, attempt, status) "
        f"VALUES ({sql_str(run_id)}, {sql_str(series_id)}, {sql_str(version_id)}, {sql_str(source_hash)}, {sql_str(model)}, 'extract_graph_v1', current_timestamp(), current_timestamp(), 0.0, 1, {sql_str('complete' if rejected == 0 else 'partial')})"
    )
    if nodes:
        values = ", ".join(
            "(" + ", ".join([sql_str(series_id), sql_str(node.id), str(node.episode), str(node.perceived_index), sql_str(node.true_time), sql_str(node.summary), sql_array(node.entities), str(node.valence), sql_str(node.excerpt_id)]) + ")"
            for node in nodes
        )
        warehouse.execute(f"INSERT INTO {fq}.narrative_nodes (series_id, node_id, episode, perceived_index, true_time, summary, entities, valence, excerpt_id) VALUES {values}")
    if excerpts:
        values = ", ".join("(" + ", ".join([sql_str(series_id), sql_str(item.id), str(item.episode), sql_str(item.text)]) + ")" for item in excerpts)
        warehouse.execute(f"INSERT INTO {fq}.excerpts (series_id, excerpt_id, episode, text) VALUES {values}")
    if entries:
        values = ", ".join(
            "(" + ", ".join([sql_str(series_id), sql_str(item.id), sql_str(item.kind), sql_str(item.description), sql_array(item.episodes), sql_array(item.excerpt_ids), str(item.urgency), sql_str(item.promise_kind), sql_array(item.entities)]) + ")"
            for item in entries
        )
        warehouse.execute(f"INSERT INTO {fq}.ledger_entries (series_id, entry_id, kind, description, episodes, excerpt_ids, urgency, promise_kind, entities) VALUES {values}")
    if payoffs:
        values = ", ".join("(" + ", ".join([sql_str(series_id), sql_str(item.node_id), sql_str(item.target_id), str(item.episode), sql_str(item.rationale), "false"]) + ")" for item in payoffs)
        warehouse.execute(f"INSERT INTO {fq}.payoff_links (series_id, node_id, target_id, episode, rationale, verified) VALUES {values}")
    status = "failed" if rejected else "complete"
    values = ", ".join(
        "(" + ", ".join([sql_str(run_id), sql_str(series_id), sql_str(version_id), str(int(row["episode"])), sql_str(status), sql_str("schema" if rejected else None), sql_str("model response rejected" if rejected else None), str(bool(rejected)).lower(), sql_array([item.id for item in excerpts if item.episode == int(row["episode"])])]) + ")"
        for row in rows
    )
    warehouse.execute(f"INSERT INTO {fq}.canonpulse_extraction_row (run_id, series_id, version_id, episode, status, failure_code, failure_message, retryable, citation_ids) VALUES {values}")
    return {"run_id": run_id, "rows": len(rows), "rejected": rejected, "nodes": len(nodes), "entries": len(entries), "payoffs": len(payoffs), "excerpts": len(excerpts)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warehouse", required=True)
    parser.add_argument("--catalog", default="writers_room")
    parser.add_argument("--schema", default="canonpulse")
    parser.add_argument("--series-id", required=True)
    parser.add_argument("--response-table", required=True)
    parser.add_argument("--model", default="databricks-gpt-oss-20b")
    args = parser.parse_args()
    print(json.dumps(persist(warehouse=Warehouse(args.warehouse), catalog=args.catalog, schema=args.schema, series_id=args.series_id, response_table=args.response_table, model=args.model), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
