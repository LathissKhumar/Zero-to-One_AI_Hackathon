"""Training corpus preparation.

**Nothing in this repository ingests a real corpus yet.** The only corpus that
exists here is the synthetic one in ``app/training_corpus.py``. This module is
built for three *intended* real sources, none of them wired up: the arXiv serial
corpus (continue-to-read rate), Qidian (raw reader-response counts), and Royal
Road (chapter view ratios).

Those three report on incompatible label scales, so pooling raw values would
teach a model platform identity rather than narrative structure. Two rules make
them comparable, and they apply equally to the synthetic corpus:

1. Z-score the target within each book. What transfers is "was this boundary
   stronger than the rest of its own story", not the absolute rate.
2. Split grouped by book_id. Chapters from one book on both sides of the split
   leak, and held-out MAE becomes fiction.
"""

from __future__ import annotations

import random
from collections import defaultdict
from statistics import fmean, pstdev


def normalize_within_book(rows: list[dict]) -> list[dict]:
    """Add a `continue_z` column: the target, z-scored within each book."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["book_id"]].append(row)

    normalized: list[dict] = []
    for book_rows in grouped.values():
        rates = [row["continue_rate"] for row in book_rows]
        mean = fmean(rates)
        spread = pstdev(rates)
        for row in book_rows:
            # A book with one chapter, or a flat one, carries no within-book
            # signal. Zero is the honest encoding of "no information".
            z = 0.0 if spread == 0 else (row["continue_rate"] - mean) / spread
            normalized.append({**row, "continue_z": z})
    return normalized


def assign_grouped_split(
    rows: list[dict], test_fraction: float = 0.2, seed: int = 42
) -> list[dict]:
    """Assign `split` per row, holding out whole books."""
    books = sorted({row["book_id"] for row in rows})
    rng = random.Random(seed)
    rng.shuffle(books)
    holdout = set(books[: max(1, round(len(books) * test_fraction))])
    return [{**row, "split": "test" if row["book_id"] in holdout else "train"} for row in rows]
