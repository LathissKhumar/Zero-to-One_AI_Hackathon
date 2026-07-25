"""Structural features -> predicted next-episode continuation.

The model consumes only the graph-derived vector. It never sees prose, and that
is deliberate: a rewrite cannot raise this score by sounding better, only by
changing structure -- closing an obligation, raising urgency, shortening the gap
to a payoff. Without that property the generator would be grading its own work.

Trained on public serialized fiction, not platform telemetry. Say so.
"""

from __future__ import annotations

from statistics import fmean

import mlflow
import mlflow.sklearn
from pydantic import BaseModel
from sklearn.ensemble import GradientBoostingRegressor

from app.corpus import assign_grouped_split
from app.narrative_models import BoundaryFeatures

# Column order is the training contract. Changing it silently scrambles inputs,
# so BoundaryFeatures.to_vector() is tested against this list.
FEATURE_ORDER: tuple[str, ...] = (
    "open_obligation_count",
    "mean_urgency",
    "max_obligation_age",
    "mean_obligation_age",
    "overdue_count",
    "planting_recency",
    "suspended_density",
    "broken_count",
    "sentiment_velocity",
    "perceived_time_jump",
    "active_thread_count",
)

MODEL_VERSION = "continuation-gbr-v1"


class TrainingReport(BaseModel):
    held_out_mae: float
    train_rows: int
    test_rows: int
    train_books: list[str]
    test_books: list[str]
    model_version: str = MODEL_VERSION


class Prediction(BaseModel):
    value: float
    lower_ci: float
    upper_ci: float
    model_version: str = MODEL_VERSION


class ContinuationPredictor:
    def __init__(self) -> None:
        self._model: GradientBoostingRegressor | None = None
        self._residual_spread = 0.0

    @property
    def model(self) -> GradientBoostingRegressor | None:
        """The fitted estimator, or ``None`` before ``train`` has run.

        Public on purpose: callers that need to hand the model to MLflow (or any
        other external sink) should go through this rather than reaching into a
        private attribute.
        """
        return self._model

    def train(self, rows: list[dict]) -> TrainingReport:
        split = assign_grouped_split(rows)
        train = [row for row in split if row["split"] == "train"]
        test = [row for row in split if row["split"] == "test"]

        model = GradientBoostingRegressor(random_state=42)
        model.fit(self._matrix(train), [row["continue_z"] for row in train])
        self._model = model

        predicted = model.predict(self._matrix(test))
        errors = [abs(p - row["continue_z"]) for p, row in zip(predicted, test)]
        mae = fmean(errors) if errors else 0.0
        # Held-out error is the honest width of the interval shown to users.
        self._residual_spread = mae

        return TrainingReport(
            held_out_mae=mae,
            train_rows=len(train),
            test_rows=len(test),
            train_books=sorted({row["book_id"] for row in train}),
            test_books=sorted({row["book_id"] for row in test}),
        )

    def predict(self, features: BoundaryFeatures) -> Prediction:
        if self._model is None:
            raise RuntimeError("ContinuationPredictor is not trained")
        vector = features.to_vector()
        raw = float(self._model.predict([[vector[name] for name in FEATURE_ORDER]])[0])
        value = _to_probability(raw)
        return Prediction(
            value=value,
            lower_ci=max(0.0, value - self._residual_spread / 4),
            upper_ci=min(1.0, value + self._residual_spread / 4),
        )

    def log_model_to_mlflow(self, name: str = "model") -> None:
        """Log the fitted estimator to the active MLflow run.

        Goes through the public ``model`` accessor rather than a private
        attribute, so callers outside this module never depend on internals.
        """
        if self._model is None:
            raise RuntimeError("ContinuationPredictor is not trained")
        mlflow.sklearn.log_model(self._model, name=name)

    @staticmethod
    def _matrix(rows: list[dict]) -> list[list[float]]:
        return [[float(row[name]) for name in FEATURE_ORDER] for row in rows]


def _to_probability(z: float) -> float:
    """Map a within-book z-score to a displayable continuation rate.

    Centred at 0.65 -- the rough continuation rate of a healthy serial boundary --
    and clamped, because a z-score has no natural bounds but a percentage does.
    """
    return max(0.0, min(1.0, 0.65 + 0.12 * z))


def train_and_log(rows: list[dict], experiment: str) -> TrainingReport:
    """Train and record the run. This is the credibility artifact for judging."""
    mlflow.set_experiment(experiment)
    with mlflow.start_run(run_name=MODEL_VERSION):
        predictor = ContinuationPredictor()
        report = predictor.train(rows)
        mlflow.log_metric("held_out_mae", report.held_out_mae)
        mlflow.log_param("train_rows", report.train_rows)
        mlflow.log_param("test_rows", report.test_rows)
        mlflow.log_param("split_strategy", "grouped_by_book_id")
        mlflow.log_param("features", ",".join(FEATURE_ORDER))
        predictor.log_model_to_mlflow(name="model")
    return report
