from __future__ import annotations

from app.real_corpus import build_real_corpus_rows, load_real_corpus_rows, split_into_chapters


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


def test_load_real_corpus_rows_returns_empty_list_when_directory_missing(tmp_path):
    assert load_real_corpus_rows(tmp_path / "does-not-exist") == []


def test_load_real_corpus_rows_reads_and_splits_real_text_files(tmp_path):
    (tmp_path / "1.txt").write_text(
        "CHAPTER I\nFirst chapter body.\nCHAPTER II\nSecond chapter body.\n", encoding="utf-8"
    )
    (tmp_path / "2.txt").write_text("Just one block, no chapter markers.", encoding="utf-8")

    rows = load_real_corpus_rows(tmp_path)
    book_ids = {row["book_id"] for row in rows}
    assert book_ids == {"gutenberg-1", "gutenberg-2"}
    assert len([row for row in rows if row["book_id"] == "gutenberg-1"]) == 2
    assert len([row for row in rows if row["book_id"] == "gutenberg-2"]) == 1
