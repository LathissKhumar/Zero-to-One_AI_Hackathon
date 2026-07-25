from __future__ import annotations

import pytest

from app.features import FeatureExtractor
from app.predictor import ContinuationPredictor, FEATURE_ORDER
from tests.test_ledger import build_series


def training_rows() -> list[dict]:
    """Synthetic rows where continuation falls as obligations go unpaid."""
    rows = []
    for book in range(6):
        for chapter in range(10):
            open_count = chapter % 5
            rows.append(
                {
                    "book_id": f"b{book}",
                    "open_obligation_count": open_count,
                    "mean_urgency": 3.0,
                    "max_obligation_age": chapter,
                    "mean_obligation_age": float(chapter),
                    "overdue_count": 1 if chapter > 7 else 0,
                    "planting_recency": chapter % 3,
                    "suspended_density": 0.1,
                    "broken_count": 0,
                    "fair_clue_density": 0.8,
                    "sentiment_velocity": 0.0,
                    "perceived_time_jump": 0.0,
                    "active_thread_count": 2,
                    "continue_z": float(open_count) - 2.0,
                }
            )
    return rows


def test_feature_order_matches_the_model_contract():
    """Column order is the training contract; a mismatch silently scrambles inputs."""
    vector = FeatureExtractor().extract(build_series(), episode=5).to_vector()
    assert list(vector.keys()) == list(FEATURE_ORDER)


def test_training_reports_held_out_error():
    predictor = ContinuationPredictor()
    report = predictor.train(training_rows())
    assert report.held_out_mae >= 0.0
    assert report.train_books and report.test_books
    assert not (set(report.train_books) & set(report.test_books))


def test_prediction_carries_an_interval():
    predictor = ContinuationPredictor()
    predictor.train(training_rows())
    prediction = predictor.predict(FeatureExtractor().extract(build_series(), episode=5))
    assert 0.0 <= prediction.value <= 1.0
    assert prediction.lower_ci <= prediction.value <= prediction.upper_ci


def test_predicting_before_training_fails_loudly():
    with pytest.raises(RuntimeError, match="not trained"):
        ContinuationPredictor().predict(FeatureExtractor().extract(build_series(), episode=5))


def test_model_property_is_none_before_training():
    """The public accessor mirrors the private state without exposing internals."""
    predictor = ContinuationPredictor()
    assert predictor.model is None


def test_model_property_exposes_fitted_estimator_after_training():
    predictor = ContinuationPredictor()
    predictor.train(training_rows())
    assert predictor.model is not None
    assert hasattr(predictor.model, "predict")
