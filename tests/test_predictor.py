from __future__ import annotations

import pytest

from app.features import FeatureExtractor
from app.predictor import ContinuationPredictor, FEATURE_ORDER, train_predictor
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


def rows_with_known_rates() -> list[dict]:
    """Rows carrying raw continue_rate so calibration has real data to derive
    a centre and scale from, instead of an unexplained constant."""
    rows = []
    for book in range(6):
        for chapter in range(10):
            open_count = chapter % 5
            rate = 0.4 + 0.05 * open_count
            rows.append(
                {
                    "book_id": f"b{book}",
                    "continue_rate": rate,
                    "open_obligation_count": open_count,
                    "mean_urgency": 3.0,
                    "max_obligation_age": chapter,
                    "mean_obligation_age": float(chapter),
                    "overdue_count": 1 if chapter > 7 else 0,
                    "planting_recency": chapter % 3,
                    "suspended_density": 0.1,
                    "broken_count": 0,
                    "sentiment_velocity": 0.0,
                    "perceived_time_jump": 0.0,
                    "active_thread_count": 2,
                    "continue_z": float(open_count) - 2.0,
                }
            )
    return rows


def test_calibration_is_derived_from_the_corpus_not_a_magic_constant():
    """The old transform was `0.65 + 0.12 * z` with both constants unexplained.
    The centre/scale must now come from the training corpus's own continue_rate
    distribution, so two corpora with different rate distributions calibrate
    differently."""
    low_predictor = ContinuationPredictor()
    low_predictor.train(rows_with_known_rates())

    shifted_rows = [{**row, "continue_rate": row["continue_rate"] + 0.3} for row in rows_with_known_rates()]
    high_predictor = ContinuationPredictor()
    high_predictor.train(shifted_rows)

    features = FeatureExtractor().extract(build_series(), episode=5)
    low_value = low_predictor.predict(features).value
    high_value = high_predictor.predict(features).value
    assert high_value > low_value


def test_prediction_reports_whether_clamping_fired():
    predictor = ContinuationPredictor()
    predictor.train(rows_with_known_rates())
    prediction = predictor.predict(FeatureExtractor().extract(build_series(), episode=5))
    assert isinstance(prediction.clamped, bool)


def test_confidence_interval_is_named_and_not_mae_over_four():
    """MAE is not a standard deviation; `/4` had no justification. The interval
    must now be derived from an empirical quantile of held-out residuals, and
    the method must be named on the report so a caller knows what it is."""
    predictor = ContinuationPredictor()
    report = predictor.train(rows_with_known_rates())
    assert report.ci_method
    assert report.residual_quantile_z >= 0.0
    prediction = predictor.predict(FeatureExtractor().extract(build_series(), episode=5))
    assert prediction.ci_method == report.ci_method


def test_governed_training_logs_and_returns_a_usable_predictor(tmp_path):
    """Configured runtime training records a run without changing prediction use."""
    import mlflow

    mlflow.set_tracking_uri(f"sqlite:///{tmp_path / 'mlflow.db'}")
    predictor, report = train_predictor(training_rows(), experiment="canonpulse-test")

    assert predictor.model is not None
    assert report.model_version
    runs = mlflow.search_runs(experiment_names=["canonpulse-test"])
    assert len(runs) == 1
    assert runs.iloc[0]["metrics.held_out_mae"] >= 0
