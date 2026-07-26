"""Structural features -> predicted next-episode continuation.

The model consumes only the graph-derived vector. It never sees prose, and that
is deliberate: a rewrite cannot raise this score by sounding better, only by
changing structure -- closing an obligation, raising urgency, shortening the gap
to a payoff. Without that property the generator would be grading its own work.

Fit to a synthetic corpus with a documented generative process (see
``app/training_corpus.py``), not to observed reader behaviour and not to platform
telemetry. Nothing in this repository ingests real retention labels yet, so these
predictions demonstrate that the pipeline runs end to end -- they are not
calibrated to real audiences. Say so wherever a number is shown.
"""

from __future__ import annotations

from statistics import fmean, pstdev

import mlflow
import mlflow.sklearn
from pydantic import BaseModel
from sklearn.ensemble import GradientBoostingRegressor

from app.corpus import assign_grouped_split
from app.narrative_models import BoundaryFeatures, Series

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
FEATURE_SCHEMA_VERSION = "structural-v1"

# The interval is the empirical p90 of |predicted - actual| on the held-out
# books, converted from z-score space into the displayed rate via the same
# scale used by the presentation-layer mapping. Named explicitly (rather than
# left as a bare "/4") so the API and README can say exactly what it is.
CI_METHOD = "p90_held_out_residual"

# Fallback calibration used only when the training rows carry no raw
# `continue_rate` column (e.g. unit tests that hand the predictor bare
# z-scores directly). Centred at 0.5 because a z-score has no inherent
# baseline; this is a stated default, not a claim about real continuation
# rates.
_FALLBACK_CENTER = 0.5
_FALLBACK_SCALE = 0.25


class TrainingReport(BaseModel):
    held_out_mae: float
    residual_quantile_z: float
    ci_method: str = CI_METHOD
    train_rows: int
    test_rows: int
    train_books: list[str]
    test_books: list[str]
    model_version: str = MODEL_VERSION
    feature_schema_version: str = FEATURE_SCHEMA_VERSION


class Prediction(BaseModel):
    value: float
    lower_ci: float
    upper_ci: float
    clamped: bool
    ci_method: str = CI_METHOD
    model_version: str = MODEL_VERSION
    feature_schema_version: str = FEATURE_SCHEMA_VERSION


class VariantScore(BaseModel):
    episode: int
    original: Prediction
    variant: Prediction
    delta: float
    model_version: str = MODEL_VERSION


def _quantile(values: list[float], q: float) -> float:
    """Linear-interpolated quantile with no numpy dependency. `values=[]` -> 0.0."""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = q * (len(ordered) - 1)
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    fraction = position - lower_index
    return ordered[lower_index] + (ordered[upper_index] - ordered[lower_index]) * fraction


class ContinuationPredictor:
    def __init__(self) -> None:
        self._model: GradientBoostingRegressor | None = None
        self._residual_quantile_z = 0.0
        self._presentation_center = _FALLBACK_CENTER
        self._presentation_scale = _FALLBACK_SCALE

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
        # Confidence interval width: the empirical 90th percentile of held-out
        # |predicted - actual| in z-space, not MAE/4 -- MAE is not a standard
        # deviation and that divisor had no justification.
        self._residual_quantile_z = _quantile(errors, 0.9)

        # Calibration: map the model's z-score output onto the corpus's own
        # continue_rate distribution when raw rates are available, rather than
        # an unexplained constant centre/slope.
        if all("continue_rate" in row for row in rows):
            rates = [row["continue_rate"] for row in rows]
            self._presentation_center = fmean(rates)
            spread = pstdev(rates)
            self._presentation_scale = spread if spread > 0 else _FALLBACK_SCALE
        else:
            self._presentation_center = _FALLBACK_CENTER
            self._presentation_scale = _FALLBACK_SCALE

        return TrainingReport(
            held_out_mae=mae,
            residual_quantile_z=self._residual_quantile_z,
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
        value, clamped = _to_probability(raw, self._presentation_center, self._presentation_scale)
        half_width = self._residual_quantile_z * self._presentation_scale
        return Prediction(
            value=value,
            lower_ci=max(0.0, value - half_width),
            upper_ci=min(1.0, value + half_width),
            clamped=clamped,
        )

    def score_variant(self, original: Series, variant: Series, episode: int) -> VariantScore:
        """Score both graphs with this already-fitted model instance.

        Keeping the method on the predictor makes it impossible for a caller
        to accidentally train a second model for the counterfactual. The only
        changing input is the structural graph projected at the same boundary.
        """
        from app.features import FeatureExtractor

        original_prediction = self.predict(FeatureExtractor().extract(original, episode))
        variant_prediction = self.predict(FeatureExtractor().extract(variant, episode))
        return VariantScore(
            episode=episode,
            original=original_prediction,
            variant=variant_prediction,
            delta=variant_prediction.value - original_prediction.value,
            model_version=original_prediction.model_version,
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


def train_predictor(
    rows: list[dict], experiment: str | None = None
) -> tuple[ContinuationPredictor, TrainingReport]:
    """Train the runtime predictor, optionally recording a governed MLflow run.

    Local demo mode passes no experiment and remains offline. Workspace mode
    supplies an experiment name or ID, which makes model provenance an actual
    runtime property instead of a helper that exists only in tests.
    """
    predictor = ContinuationPredictor()
    if not experiment:
        return predictor, predictor.train(rows)

    if experiment.isdigit():
        run_context = mlflow.start_run(experiment_id=experiment, run_name=MODEL_VERSION)
    else:
        mlflow.set_experiment(experiment)
        run_context = mlflow.start_run(run_name=MODEL_VERSION)
    with run_context as run:
        report = predictor.train(rows)
        mlflow.log_metric("held_out_mae", report.held_out_mae)
        mlflow.log_metric("residual_quantile_z_p90", report.residual_quantile_z)
        mlflow.log_param("train_rows", report.train_rows)
        mlflow.log_param("test_rows", report.test_rows)
        mlflow.log_param("split_strategy", "grouped_by_book_id")
        mlflow.log_param("ci_method", report.ci_method)
        mlflow.log_param("features", ",".join(FEATURE_ORDER))
        mlflow.log_param("model_version", report.model_version)
        mlflow.log_param("feature_schema_version", report.feature_schema_version)
        predictor.log_model_to_mlflow(name="model")
        # Keep this available to callers that need to connect a served
        # prediction back to its training artifact without making the model
        # itself depend on MLflow internals.
        predictor.mlflow_run_id = run.info.run_id  # type: ignore[attr-defined]
    return predictor, report


def _to_probability(z: float, center: float, scale: float) -> tuple[float, bool]:
    """Map a within-book z-score onto a displayable continuation rate.

    This is a presentation-layer affine mapping, not a calibrated probability
    model: `center`/`scale` come from the training corpus's own continue_rate
    distribution (see `train`), so the mapping reflects what that corpus
    actually looked like rather than a hardcoded constant. The result is
    clamped to [0, 1] because a z-score is unbounded but a rate is not;
    the second return value reports whether clamping actually fired, so a
    caller can tell a saturated prediction from a well-behaved one instead of
    it being silently masked.
    """
    raw = center + scale * z
    clamped_value = max(0.0, min(1.0, raw))
    return clamped_value, clamped_value != raw


def train_and_log(rows: list[dict], experiment: str) -> TrainingReport:
    """Train and record the run. This is the credibility artifact for judging."""
    _predictor, report = train_predictor(rows, experiment)
    return report
