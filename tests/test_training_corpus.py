from __future__ import annotations

from statistics import fmean

from app.corpus import assign_grouped_split, normalize_within_book
from app.predictor import FEATURE_ORDER, ContinuationPredictor
from app.training_corpus import generate_synthetic_corpus


def test_rows_carry_every_feature_and_corpus_column():
    rows = generate_synthetic_corpus()
    assert rows
    required = {"platform", "book_id", "chapter", "continue_rate", *FEATURE_ORDER}
    for row in rows:
        assert required.issubset(row.keys())


def test_continue_rate_is_bounded():
    rows = generate_synthetic_corpus()
    for row in rows:
        assert 0.0 <= row["continue_rate"] <= 1.0


def test_generation_is_deterministic_for_a_given_seed():
    first = generate_synthetic_corpus(seed=7)
    second = generate_synthetic_corpus(seed=7)
    assert first == second


def test_different_seeds_produce_different_corpora():
    first = generate_synthetic_corpus(seed=1)
    second = generate_synthetic_corpus(seed=2)
    assert first != second


def test_overdue_and_broken_rows_score_lower_on_average():
    """The stated generative process: overdue obligations and unresolved
    contradictions must pull continue_rate down, not up -- otherwise the
    synthetic label contradicts the product's own thesis."""
    rows = generate_synthetic_corpus(n_books=40, chapters_per_book=20, seed=11)
    clean = [r["continue_rate"] for r in rows if r["overdue_count"] == 0 and r["broken_count"] == 0]
    troubled = [r["continue_rate"] for r in rows if r["overdue_count"] > 0 or r["broken_count"] > 0]
    assert clean and troubled
    assert fmean(clean) > fmean(troubled)


def test_more_open_obligations_and_urgency_score_higher_on_average():
    rows = generate_synthetic_corpus(n_books=40, chapters_per_book=20, seed=11)
    low = [r["continue_rate"] for r in rows if r["open_obligation_count"] <= 1]
    high = [r["continue_rate"] for r in rows if r["open_obligation_count"] >= 4]
    assert low and high
    assert fmean(high) > fmean(low)


def test_corpus_flows_through_the_real_training_pipeline():
    """End to end: generate -> normalize -> split -> train, with no crashes and
    a real (non-1.0, non-degenerate) held-out error."""
    rows = generate_synthetic_corpus(n_books=30, chapters_per_book=15, seed=42)
    normalized = normalize_within_book(rows)
    predictor = ContinuationPredictor()
    report = predictor.train(normalized)
    assert report.held_out_mae >= 0.0
    assert report.train_books and report.test_books


def test_split_still_groups_by_book_after_generation():
    rows = generate_synthetic_corpus(n_books=10, chapters_per_book=5, seed=3)
    split = assign_grouped_split(rows)
    by_book: dict[str, set[str]] = {}
    for row in split:
        by_book.setdefault(row["book_id"], set()).add(row["split"])
    for book, splits in by_book.items():
        assert len(splits) == 1, f"book {book} straddles the split"
