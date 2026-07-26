# CanonPulse Training, Features, and Prediction Specification

## Purpose

Train a continuation model from structural graph features and report a
calibrated, explicitly caveated next-episode estimate. The model is blind to
prose and explanations.

## Training sources

The training ingestion seam accepts three source adapters:

- arXiv serial-fiction corpus: direct continue-to-read labels;
- Qidian/Webnovel corpus: reader-response labels normalized to boundary
  continuation proxies;
- Royal Road corpus: within-book view ratios, subject to licensing and quality
  checks.

Each adapter emits `platform`, `book_id`, `chapter`, raw label, text reference,
and structural feature inputs. Targets are z-scored within `book_id`. Splits
are grouped by book; no book may occur in both train and test. Synthetic data
remains a deterministic development fixture and is never described as reader
telemetry.

## Feature contract

At a boundary, the numeric graph features are:

- open obligation count;
- urgency-weighted mean of open obligations;
- minimum known scheduled-payoff distance;
- mean known scheduled-payoff distance;
- planting recency;
- suspended-edge density;
- broken-edge count;
- fair-clue density;
- sentiment velocity;
- perceived-time jump;
- active character-thread count.

`platform` is a training-only categorical input. Scheduled payoff distance may
use only a payoff commitment known at the boundary; it may not inspect the
future outcome of an ongoing story. The feature projector rejects prose,
summaries, raw episode indices as model inputs, and any feature that reads past
the requested boundary.

## Model and uncertainty

`ContinuationModel` trains a versioned regressor, stores feature order and
training metadata, and exposes:

```text
train(training_table) -> TrainingReport
predict(feature_vector) -> Prediction
score_variant(feature_table) -> PredictionSeries
```

The report includes grouped held-out MAE, per-platform metrics, train/test
book IDs, residual quantiles, model version, and feature schema version. The
prediction includes value, interval, calibration method, clamping status, and
disclosure. The interval method must be named and derived from held-out
residuals; it must not be an unexplained constant.

## Counterfactual requirement

Original and rewritten graphs are projected through the same frozen model
version. The system returns per-boundary deltas, confidence intervals, feature
movement, and an unattributed remainder. No caller may supply the total delta
or replace the model used for comparison.

## Acceptance criteria

- Real-source ingestion is optional at local test time but has a complete
  adapter and schema contract.
- Grouped-by-book leakage tests fail if a book crosses splits.
- Feature vectors are identical for identical graph snapshots and contain no
  prose.
- Future episode mutations do not change earlier-boundary features.
- A rewrite can move a prediction only by changing the structural graph.
- Every displayed prediction carries the synthetic/real-data provenance and
  model version.
- The held-out report and model artifact are logged to MLflow in governed
  mode.

## Tests

Test normalization, grouped splits, feature order, no-lookahead, platform
encoding, model training, calibration, interval bounds, model freezing,
counterfactual deltas, and MLflow metadata through public interfaces. Use
synthetic fixtures to make tests deterministic; never fabricate a real corpus
or label to make a metric pass.
