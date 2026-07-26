"""Promote parsed Databricks documents into CanonPulse and run graph extraction.

The script is intentionally explicit about the boundary:
``ai_parse_document`` produces document structure; CanonPulse decides episode
boundaries, writes the episode table, then calls the governed graph extractor.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.document_ingestion import normalize_parsed_document  # noqa: E402
from app.extraction import parse_extraction_row  # noqa: E402
from app.narrative_models import Excerpt, LedgerEntry, NarrativeNode, PayoffLink  # noqa: E402


def sql_str(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def sql_array(values: list[object] | None) -> str:
    if not values:
        return "array()"
    return "array(" + ", ".join(sql_str(value) for value in values) + ")"


def response_rows(response: dict) -> list[dict]:
    schema = ((response.get("manifest") or {}).get("schema") or {}).get("columns") or []
    names = [column["name"] for column in schema]
    return [dict(zip(names, row)) for row in ((response.get("result") or {}).get("data_array") or [])]


def extraction_object(raw: object) -> dict | None:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        return parse_extraction_row(raw)
    return None


class Warehouse:
    def __init__(self, warehouse_id: str) -> None:
        self.warehouse_id = warehouse_id

    def _cli(self, command: list[str]) -> dict:
        result = subprocess.run(
            ["databricks", *command],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip()[:1000])
        return json.loads(result.stdout)

    def execute(self, statement: str, parameters: list[dict] | None = None) -> dict:
        payload = {
            "warehouse_id": self.warehouse_id,
            "statement": statement,
            "wait_timeout": "50s",
        }
        if parameters:
            payload["parameters"] = parameters
        response = self._cli(["api", "post", "/api/2.0/sql/statements", "--json", json.dumps(payload)])
        statement_id = response.get("statement_id")
        while response.get("status", {}).get("state") in {"PENDING", "RUNNING"}:
            time.sleep(2)
            response = self._cli(["api", "get", f"/api/2.0/sql/statements/{statement_id}"])
        if response.get("status", {}).get("state") != "SUCCEEDED":
            raise RuntimeError(json.dumps(response.get("status", {}))[:1500])
        return response


def promote(
    warehouse: Warehouse,
    *,
    catalog: str,
    schema: str,
    series_id: str,
    title: str,
    genre: str,
    model: str,
) -> dict:
    fq = f"{catalog}.{schema}"
    parsed_rows = response_rows(
        warehouse.execute(
            f"SELECT document_id, source_path, source_hash, to_json(parsed_document) AS parsed_json "
            f"FROM {fq}.canonpulse_parsed_document WHERE series_id = :series_id",
            [{"name": "series_id", "value": series_id}],
        )
    )
    if not parsed_rows:
        raise RuntimeError(f"no parsed documents found for series_id={series_id}")

    normalized = []
    warnings: list[str] = []
    for row in parsed_rows:
        parsed = json.loads(row["parsed_json"])
        result = normalize_parsed_document(
            parsed,
            source_path=str(row["source_path"]),
            series_id=series_id,
            title=title,
            genre=genre,
        )
        normalized.extend(result.submission.episodes)
        warnings.extend(result.warnings)

    normalized.sort(key=lambda episode: episode.episode_number)
    episode_numbers = [episode.episode_number for episode in normalized]
    if len(episode_numbers) != len(set(episode_numbers)):
        raise RuntimeError("parsed documents produced duplicate episode numbers; review required")

    source_hash = str(parsed_rows[0]["source_hash"])
    version_id = f"document-{source_hash[:16]}"
    run_id = f"extract-{uuid.uuid4().hex[:16]}"
    for table in ("narrative_nodes", "excerpts", "ledger_entries", "payoff_links", "episodes", "series", "canonpulse_submission"):
        warehouse.execute(f"DELETE FROM {fq}.{table} WHERE series_id = {sql_str(series_id)}")

    warehouse.execute(
        f"INSERT INTO {fq}.series (series_id, title, genre, total_episodes, ongoing, source) "
        f"VALUES ({sql_str(series_id)}, {sql_str(title)}, {sql_str(genre)}, {max(episode_numbers)}, true, 'document')"
    )
    warehouse.execute(
        f"INSERT INTO {fq}.canonpulse_submission (series_id, version_id, source_hash, title, genre, ongoing) "
        f"VALUES ({sql_str(series_id)}, {sql_str(version_id)}, {sql_str(source_hash)}, {sql_str(title)}, {sql_str(genre)}, true)"
    )
    for start in range(0, len(normalized), 25):
        values = []
        for episode in normalized[start : start + 25]:
            values.append(
                "(" + ", ".join(
                    [
                        sql_str(series_id), str(episode.episode_number), sql_str(f"Episode {episode.episode_number}"),
                        sql_str(episode.text), sql_str(episode.text[:1000]), "true", str(len(episode.text.split())), sql_str(episode.writer_id),
                    ]
                ) + ")"
            )
        warehouse.execute(
            f"INSERT INTO {fq}.episodes (series_id, episode, title, body, synopsis, has_full_text, word_count, writer_id) "
            f"VALUES {', '.join(values)}"
        )

    extraction_sql = (ROOT / "sql" / "extract_graph.sql").read_text(encoding="utf-8")
    extraction_sql = extraction_sql.replace("${catalog}", catalog).replace("${db}", schema).replace("${model}", model).rstrip().rstrip(";")
    # Materialize the model response first. A long ai_query result can outlive
    # the client-side response window; Delta is the durable handoff between
    # governed inference and the application-side schema validator.
    response_table = f"{fq}.canonpulse_graph_response"
    warehouse.execute(
        f"CREATE OR REPLACE TABLE {response_table} AS "
        f"SELECT {sql_str(series_id)} AS series_id, extracted.episode, CAST(extracted.extraction AS STRING) AS extraction "
        f"FROM ({extraction_sql}) extracted",
        [{"name": "series_id", "value": series_id}],
    )
    extraction_rows = response_rows(
        warehouse.execute(
            f"SELECT episode, extraction FROM {response_table} WHERE series_id = :series_id",
            [{"name": "series_id", "value": series_id}],
        )
    )

    nodes: list[NarrativeNode] = []
    entries: list[LedgerEntry] = []
    payoffs: list[PayoffLink] = []
    excerpts: list[Excerpt] = []
    rejected = 0
    for row in extraction_rows:
        parsed = extraction_object(row.get("extraction"))
        if parsed is None:
            rejected += 1
            continue
        try:
            nodes.extend(NarrativeNode.model_validate(item) for item in parsed.get("nodes", []))
            entries.extend(LedgerEntry.model_validate(item) for item in parsed.get("entries", []))
            payoffs.extend(PayoffLink.model_validate({**item, "verified": False}) for item in parsed.get("payoffs", []))
            excerpts.extend(Excerpt.model_validate(item) for item in parsed.get("excerpts", []))
        except Exception:  # noqa: BLE001 - one malformed model row is rejected, not fatal to the batch
            rejected += 1

    for node in nodes:
        warehouse.execute(
            f"INSERT INTO {fq}.narrative_nodes (series_id, node_id, episode, perceived_index, true_time, summary, entities, valence, excerpt_id) "
            f"VALUES ({sql_str(series_id)}, {sql_str(node.id)}, {node.episode}, {node.perceived_index}, {sql_str(node.true_time)}, {sql_str(node.summary)}, {sql_array(node.entities)}, {node.valence}, {sql_str(node.excerpt_id)})"
        )
    for excerpt in excerpts:
        warehouse.execute(
            f"INSERT INTO {fq}.excerpts (series_id, excerpt_id, episode, text) "
            f"VALUES ({sql_str(series_id)}, {sql_str(excerpt.id)}, {excerpt.episode}, {sql_str(excerpt.text)})"
        )
    for entry in entries:
        warehouse.execute(
            f"INSERT INTO {fq}.ledger_entries (series_id, entry_id, kind, description, episodes, excerpt_ids, urgency, promise_kind, entities) "
            f"VALUES ({sql_str(series_id)}, {sql_str(entry.id)}, {sql_str(entry.kind)}, {sql_str(entry.description)}, {sql_array(entry.episodes)}, {sql_array(entry.excerpt_ids)}, {entry.urgency}, {sql_str(entry.promise_kind)}, {sql_array(entry.entities)})"
        )
    for payoff in payoffs:
        warehouse.execute(
            f"INSERT INTO {fq}.payoff_links (series_id, node_id, target_id, episode, rationale, verified) "
            f"VALUES ({sql_str(series_id)}, {sql_str(payoff.node_id)}, {sql_str(payoff.target_id)}, {payoff.episode}, {sql_str(payoff.rationale)}, false)"
        )

    now = datetime.now(timezone.utc).isoformat()
    warehouse.execute(
        f"INSERT INTO {fq}.canonpulse_extraction_run (run_id, series_id, version_id, source_hash, model_name, prompt_version, started_at, finished_at, latency_ms, attempt, status) "
        f"VALUES ({sql_str(run_id)}, {sql_str(series_id)}, {sql_str(version_id)}, {sql_str(source_hash)}, {sql_str(model)}, 'extract_graph_v1', {sql_str(now)}, current_timestamp(), 0.0, 1, 'complete')"
    )
    for episode in normalized:
        warehouse.execute(
            f"INSERT INTO {fq}.canonpulse_extraction_row (run_id, series_id, version_id, episode, status, failure_code, failure_message, retryable, citation_ids) "
            f"VALUES ({sql_str(run_id)}, {sql_str(series_id)}, {sql_str(version_id)}, {episode.episode_number}, 'complete', NULL, NULL, false, array())"
        )

    return {
        "series_id": series_id,
        "version_id": version_id,
        "episodes_promoted": len(normalized),
        "review_required": bool(warnings),
        "warnings": sorted(set(warnings)),
        "extraction_rows": len(extraction_rows),
        "rejected_extraction_rows": rejected,
        "nodes": len(nodes),
        "entries": len(entries),
        "payoffs": len(payoffs),
        "excerpts": len(excerpts),
        "run_id": run_id,
        "response_table": response_table,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warehouse", required=True)
    parser.add_argument("--catalog", default="writers_room")
    parser.add_argument("--schema", default="canonpulse")
    parser.add_argument("--series-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--genre", default="serialized fiction")
    parser.add_argument("--model", default="databricks-gpt-oss-20b")
    args = parser.parse_args()
    report = promote(
        Warehouse(args.warehouse), catalog=args.catalog, schema=args.schema, series_id=args.series_id,
        title=args.title, genre=args.genre, model=args.model,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
