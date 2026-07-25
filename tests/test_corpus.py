from __future__ import annotations

from app.corpus import assign_grouped_split, normalize_within_book


def rows() -> list[dict]:
    return [
        {"platform": "royalroad", "book_id": "b1", "chapter": 1, "continue_rate": 0.9},
        {"platform": "royalroad", "book_id": "b1", "chapter": 2, "continue_rate": 0.7},
        {"platform": "royalroad", "book_id": "b1", "chapter": 3, "continue_rate": 0.8},
        {"platform": "qidian", "book_id": "b2", "chapter": 1, "continue_rate": 0.5},
        {"platform": "qidian", "book_id": "b2", "chapter": 2, "continue_rate": 0.3},
        {"platform": "qidian", "book_id": "b2", "chapter": 3, "continue_rate": 0.4},
    ]


def test_z_scoring_happens_within_each_book():
    """Absolute rates are not comparable across platforms; within-book deltas are."""
    normalized = normalize_within_book(rows())
    b1 = [row["continue_z"] for row in normalized if row["book_id"] == "b1"]
    b2 = [row["continue_z"] for row in normalized if row["book_id"] == "b2"]
    assert abs(sum(b1)) < 1e-9
    assert abs(sum(b2)) < 1e-9
    # Both books' best chapter normalizes to the same score despite different raw rates.
    assert abs(max(b1) - max(b2)) < 1e-9


def test_single_chapter_books_get_zero_not_a_crash():
    single = [{"platform": "arxiv", "book_id": "solo", "chapter": 1, "continue_rate": 0.6}]
    assert normalize_within_book(single)[0]["continue_z"] == 0.0


def test_split_groups_by_book_so_chapters_never_straddle():
    """Chapters from one book on both sides of the split is leakage: the model
    memorises the book instead of learning structure, and held-out MAE lies."""
    split = assign_grouped_split(rows(), test_fraction=0.5, seed=7)
    by_book: dict[str, set[str]] = {}
    for row in split:
        by_book.setdefault(row["book_id"], set()).add(row["split"])
    for book, splits in by_book.items():
        assert len(splits) == 1, f"book {book} appears in both splits"


def test_split_is_deterministic_for_a_given_seed():
    first = assign_grouped_split(rows(), test_fraction=0.5, seed=7)
    second = assign_grouped_split(rows(), test_fraction=0.5, seed=7)
    assert [row["split"] for row in first] == [row["split"] for row in second]
