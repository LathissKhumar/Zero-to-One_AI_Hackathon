from __future__ import annotations

from pathlib import Path

from app.series_loader import load_series

SERIES_PATH = Path("data/series/last_monsoon.json")


def test_demo_series_spans_two_hundred_plus_episodes():
    series = load_series(SERIES_PATH)
    assert series.total_episodes == 220
    assert series.id == "last-monsoon"


def test_every_entry_cites_an_existing_excerpt():
    series = load_series(SERIES_PATH)
    known = {excerpt.id for excerpt in series.excerpts}
    for entry in series.entries:
        assert entry.excerpt_ids, f"{entry.id} has no citation"
        for excerpt_id in entry.excerpt_ids:
            assert excerpt_id in known, f"{entry.id} cites unknown excerpt {excerpt_id}"


def test_payoff_links_point_at_real_entries():
    series = load_series(SERIES_PATH)
    known = {entry.id for entry in series.entries}
    for link in series.payoffs:
        assert link.target_id in known, f"payoff targets unknown entry {link.target_id}"
