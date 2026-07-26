from __future__ import annotations

from app.real_corpus import build_real_corpus_rows


def test_build_real_corpus_rows_runs_real_extraction_on_real_prose():
    chapters_by_book = {
        "test": [
            "Ana promises she will return to the ferry one day.",
            "The old locket is found again, finally resolving the mystery.",
        ]
    }
    rows = build_real_corpus_rows(chapters_by_book)
    assert len(rows) == 2
    assert all(row["platform"] == "gutenberg" for row in rows)
    assert all(row["book_id"] == "gutenberg-test" for row in rows)
    assert [row["chapter"] for row in rows] == [1, 2]
    assert all(0.0 <= row["continue_rate"] <= 1.0 for row in rows)
    # Real feature extraction ran -- chapter 1's promise should be open at
    # its own boundary, not fabricated from a formula with no source text.
    assert rows[0]["open_obligation_count"] >= 1


def test_build_real_corpus_rows_is_deterministic():
    chapters_by_book = {"b": ["Someday she must return.", "She never learned to swim."]}
    first = build_real_corpus_rows(chapters_by_book)
    second = build_real_corpus_rows(chapters_by_book)
    assert first == second


def test_build_real_corpus_rows_handles_multiple_books_independently():
    chapters_by_book = {
        "one": ["A single short chapter with no promises."],
        "two": ["Another book's single chapter, also plain."],
    }
    rows = build_real_corpus_rows(chapters_by_book)
    book_ids = {row["book_id"] for row in rows}
    assert book_ids == {"gutenberg-one", "gutenberg-two"}
