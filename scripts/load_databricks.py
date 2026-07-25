"""Load the committed demo series into Unity Catalog.

The schema in `sql/ddl.sql` can be deployed without ever holding a row, which is
exactly the state this script exists to fix: tables that exist but are empty
prove nothing about whether the pipeline runs on the platform.

Idempotent. Every table is deleted for this `series_id` before insert, so
re-running converges rather than accumulating duplicates.

Usage:
    uv run python scripts/load_databricks.py --warehouse <id> \
        --catalog writers_room --schema canonpulse

Requires an authenticated `databricks` CLI on PATH. Reads nothing secret --
auth comes from the CLI's own profile, so no token is ever passed as an
argument or written into this file.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.manifest import load_manifest  # noqa: E402
from app.series_loader import load_series  # noqa: E402

SERIES_PATH = REPO_ROOT / "data" / "series" / "last_monsoon.json"
MANIFEST_PATH = REPO_ROOT / "data" / "manifest" / "last_monsoon.yaml"

# Statement-API payloads are capped, and a 220-episode series carries a few
# hundred KB of prose. Batch inserts rather than emitting one enormous VALUES.
BATCH = 25


def sql_str(value: object) -> str:
    """SQL literal. Doubles single quotes; NULL for None."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def sql_array(values: list[str] | None) -> str:
    if not values:
        return "array()"
    return "array(" + ", ".join(sql_str(v) for v in values) + ")"


class Warehouse:
    def __init__(self, warehouse_id: str) -> None:
        self._id = warehouse_id

    def execute(self, statement: str) -> dict:
        payload = {
            "warehouse_id": self._id,
            "statement": statement,
            "wait_timeout": "50s",
        }
        proc = subprocess.run(
            ["databricks", "api", "post", "/api/2.0/sql/statements", "--json", json.dumps(payload)],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"CLI failed: {proc.stderr.strip()[:500]}")
        result = json.loads(proc.stdout)
        state = result.get("status", {}).get("state")
        if state != "SUCCEEDED":
            detail = json.dumps(result.get("status", {}))[:500]
            raise RuntimeError(f"statement {state}: {detail}")
        return result

    def insert_batched(self, table: str, columns: list[str], rows: list[list[str]]) -> int:
        for start in range(0, len(rows), BATCH):
            chunk = rows[start : start + BATCH]
            values = ", ".join("(" + ", ".join(row) + ")" for row in chunk)
            self.execute(f"INSERT INTO {table} ({', '.join(columns)}) VALUES {values}")
        return len(rows)


def load(warehouse: Warehouse, catalog: str, schema: str) -> dict[str, int]:
    series = load_series(SERIES_PATH)
    manifest = load_manifest(MANIFEST_PATH)
    fq = f"{catalog}.{schema}"
    sid = series.id
    counts: dict[str, int] = {}

    # Idempotency: clear this series first so a re-run converges.
    for table in (
        "series", "episodes", "excerpts", "narrative_nodes",
        "ledger_entries", "payoff_links", "defect_manifest", "listener_cohorts",
        "boundary_features",
    ):
        predicate = "true" if table == "listener_cohorts" else f"series_id = {sql_str(sid)}"
        warehouse.execute(f"DELETE FROM {fq}.{table} WHERE {predicate}")

    counts["series"] = warehouse.insert_batched(
        f"{fq}.series",
        ["series_id", "title", "genre", "total_episodes", "ongoing", "source"],
        [[sql_str(sid), sql_str(series.title), sql_str(series.genre),
          str(series.total_episodes), sql_str(series.ongoing), sql_str("demo")]],
    )

    excerpt_by_episode = {item.episode: item.text for item in series.excerpts}
    counts["episodes"] = warehouse.insert_batched(
        f"{fq}.episodes",
        ["series_id", "episode", "title", "body", "synopsis", "has_full_text", "word_count"],
        [
            [sql_str(sid), str(node.episode), sql_str(f"Episode {node.episode}"),
             sql_str(excerpt_by_episode.get(node.episode)), sql_str(node.summary),
             sql_str(node.episode in excerpt_by_episode),
             str(len((excerpt_by_episode.get(node.episode) or "").split()))]
            for node in series.nodes
        ],
    )

    counts["excerpts"] = warehouse.insert_batched(
        f"{fq}.excerpts",
        ["series_id", "excerpt_id", "episode", "text"],
        [[sql_str(sid), sql_str(x.id), str(x.episode), sql_str(x.text)] for x in series.excerpts],
    )

    counts["narrative_nodes"] = warehouse.insert_batched(
        f"{fq}.narrative_nodes",
        ["series_id", "node_id", "episode", "perceived_index", "true_time",
         "summary", "entities", "valence", "excerpt_id"],
        [
            [sql_str(sid), sql_str(n.id), str(n.episode), str(n.perceived_index),
             sql_str(n.true_time), sql_str(n.summary), sql_array(n.entities),
             str(n.valence), sql_str(n.excerpt_id)]
            for n in series.nodes
        ],
    )

    counts["ledger_entries"] = warehouse.insert_batched(
        f"{fq}.ledger_entries",
        ["series_id", "entry_id", "kind", "description", "episodes",
         "excerpt_ids", "urgency", "promise_kind", "entities"],
        [
            [sql_str(sid), sql_str(e.id), sql_str(e.kind), sql_str(e.description),
             "array(" + ", ".join(str(v) for v in e.episodes) + ")",
             sql_array(e.excerpt_ids), str(e.urgency), sql_str(e.promise_kind),
             sql_array(e.entities)]
            for e in series.entries
        ],
    )

    counts["payoff_links"] = warehouse.insert_batched(
        f"{fq}.payoff_links",
        ["series_id", "node_id", "target_id", "episode", "rationale", "verified"],
        [
            [sql_str(sid), sql_str(p.node_id), sql_str(p.target_id), str(p.episode),
             sql_str(p.rationale), sql_str(p.verified)]
            for p in series.payoffs
        ],
    )

    counts["defect_manifest"] = warehouse.insert_batched(
        f"{fq}.defect_manifest",
        ["series_id", "defect_id", "defect_class", "planted_episode",
         "payoff_episode", "expected_state", "notes", "authored_by"],
        [
            [sql_str(sid), sql_str(i.defect_id), sql_str(i.defect_class),
             sql_str(i.planted_episode), sql_str(i.payoff_episode),
             sql_str(i.expected_state), sql_str(i.notes), sql_str(manifest.authored_by)]
            for i in manifest.items
        ],
    )

    # boundary_features is not optional: sql/cohort_reactions.sql JOINs it, so
    # leaving it empty makes that statement return zero rows on a workspace
    # while every other table looks correctly populated.
    from app.features import FeatureExtractor

    feature_rows = FeatureExtractor().extract_all(series)
    counts["boundary_features"] = warehouse.insert_batched(
        f"{fq}.boundary_features",
        ["series_id", "episode", "open_obligation_count", "mean_urgency",
         "max_obligation_age", "mean_obligation_age", "overdue_count",
         "planting_recency", "suspended_density", "broken_count",
         "sentiment_velocity", "perceived_time_jump", "active_thread_count"],
        [
            [sql_str(sid), str(f.episode), str(f.open_obligation_count),
             str(f.mean_urgency), str(f.max_obligation_age), str(f.mean_obligation_age),
             str(f.overdue_count), str(f.planting_recency), str(f.suspended_density),
             str(f.broken_count), str(f.sentiment_velocity), str(f.perceived_time_jump),
             str(f.active_thread_count)]
            for f in feature_rows
        ],
    )

    from app.cohorts import COHORTS

    counts["listener_cohorts"] = warehouse.insert_batched(
        f"{fq}.listener_cohorts",
        ["cohort_id", "name", "weights", "profile"],
        [
            [sql_str(c.id), sql_str(c.name),
             "map(" + ", ".join(f"{sql_str(k)}, {v}" for k, v in sorted(c.weights.items())) + ")",
             sql_str(
                 "Weighs "
                 + ", ".join(f"{k} {v}" for k, v in sorted(c.weights.items(), key=lambda kv: -kv[1]))
             )]
            for c in COHORTS
        ],
    )

    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warehouse", required=True)
    parser.add_argument("--catalog", default="writers_room")
    parser.add_argument("--schema", default="canonpulse")
    args = parser.parse_args()

    warehouse = Warehouse(args.warehouse)
    counts = load(warehouse, args.catalog, args.schema)
    for table, n in counts.items():
        print(f"  {table:<20} {n}")
    print(f"\nLoaded into {args.catalog}.{args.schema}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
