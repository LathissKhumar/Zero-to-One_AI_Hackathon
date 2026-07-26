# Gap 3 — Canonical Feature Contract and Model Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the runtime feature vector, training table, persisted model signature, and attribution output with the 11-feature canonpulse contract.

**Architecture:** One versioned feature schema owns names, order, numeric/categorical encoding, and null policy. The ledger traversal produces a typed vector; training and inference both consume that schema; model loading rejects incompatible versions before scoring. Platform-specific metrics remain explicit training metadata and never leak into product copy.

**Tech Stack:** Python 3.11–3.14, Pydantic/dataclasses, scikit-learn-compatible regressor, MLflow, Delta/Databricks SQL, pytest.

## Global Constraints

- The predictor consumes graph features only and never prose.
- Feature order and API schemas must be explicit and tested.
- `platform` is a categorical training feature; product language remains platform-independent.
- Labels are normalized within `book_id`; splits are grouped by `book_id`, never by chapter.
- Runtime inference must use the same frozen model and feature schema for original and rewritten graphs.
- Preserve synthetic-data disclosure for demo cohort and manifest metrics.

---

## File map

- Create `app/feature_schema.py`: canonical names, version, encoder, and typed vector.
- Modify `app/features.py`: graph traversal and scheduled-payoff/fair-clue calculations.
- Modify `app/predictor.py` and `app/rewrite.py`: schema validation, model signature, and attribution.
- Modify `app/training_corpus.py` and `app/corpus.py`: grouped split, normalized label, platform encoding.
- Modify `sql/ddl.sql`: feature-table columns and schema version.
- Create `tests/test_feature_schema.py`; modify `tests/test_features.py`, `tests/test_predictor.py`, and `tests/test_rewrite.py`.

## Task 1: Freeze the feature schema and vector encoder

**Files:**
- Create: `app/feature_schema.py`
- Test: `tests/test_feature_schema.py`

**Interfaces:**
- Produces `FEATURE_SCHEMA_VERSION: str`, `FEATURE_ORDER: tuple[str, ...]`.
- Produces `FeatureVector(values: tuple[float, ...], platform: str, schema_version: str)`.
- Produces `encode_features(raw: Mapping[str, float], platform: str) -> FeatureVector`.

- [ ] **Step 1: Write the failing test**

```python
def test_feature_order_is_canonical():
    assert FEATURE_ORDER == (
        "open_obligation_count", "mean_urgency", "min_payoff_distance",
        "mean_payoff_distance", "planting_recency", "suspended_edge_density",
        "broken_edge_count", "fair_clue_density", "sentiment_velocity",
        "perceived_time_jump", "character_thread_count",
    )

def test_missing_numeric_feature_is_rejected():
    with pytest.raises(ValueError, match="fair_clue_density"):
        encode_features({"open_obligation_count": 1.0}, platform="arxiv")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_feature_schema.py -v`

Expected: FAIL because the canonical schema is not defined.

- [ ] **Step 3: Write minimal implementation**

Define the exact 11-feature order above, reject missing/non-finite values, preserve `platform` outside the numeric tuple, and serialize as `{"schema_version": ..., "feature_order": ..., "values": ..., "platform": ...}`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_feature_schema.py -v`

Expected: PASS for ordering, null rejection, serialization, and round-trip decoding.

- [ ] **Step 5: Commit**

```bash
git add app/feature_schema.py tests/test_feature_schema.py
git commit -m "feat: freeze canonpulse feature schema"
```

## Task 2: Compute scheduled payoff distance and fair-clue density

**Files:**
- Modify: `app/features.py`
- Test: `tests/test_features.py`

**Interfaces:**
- `compute_feature_map(graph: NarrativeGraph, boundary: int) -> dict[str, float]` returns every key in `FEATURE_ORDER`.
- `scheduled_payoff_distance(obligations: Sequence[Obligation], boundary: int) -> tuple[float, float]` returns minimum and mean distance, using `boundary + 1` for an unpaid obligation with no scheduled payoff.
- `fair_clue_density(clues: Sequence[Clue], reveals: Sequence[Reveal], boundary: int) -> float` returns a value in `[0.0, 1.0]`.

- [ ] **Step 1: Write the failing test**

```python
def test_feature_map_includes_payoff_distance_and_fair_clues():
    features = compute_feature_map(graph_with_payoff_and_fair_clue(), boundary=10)
    assert features["min_payoff_distance"] == 2.0
    assert features["fair_clue_density"] == 1.0
    assert set(features) == set(FEATURE_ORDER)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_features.py -k 'payoff_distance or fair_clue' -v`

Expected: FAIL because the runtime map still emits the legacy feature names and omits the new metrics.

- [ ] **Step 3: Write minimal implementation**

Traverse obligations and clue/reveal links without LLM calls; calculate numeric values from graph state; use zero for empty density denominators and preserve deterministic float rounding at serialization boundaries.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_features.py -v`

Expected: PASS, including empty graph, overdue obligation, and multiple reveal cases.

- [ ] **Step 5: Commit**

```bash
git add app/features.py tests/test_features.py
git commit -m "feat: compute canonical payoff and clue features"
```

## Task 3: Align training data, platform encoding, and model signature

**Files:**
- Modify: `app/training_corpus.py`, `app/corpus.py`, `app/predictor.py`
- Modify: `sql/ddl.sql`
- Test: `tests/test_corpus.py`, `tests/test_predictor.py`

**Interfaces:**
- `build_training_rows(records: Sequence[TrainingRecord]) -> list[TrainingRow]` normalizes labels within `book_id`.
- `grouped_split(rows: Sequence[TrainingRow], seed: int) -> TrainTestSplit` has disjoint `book_id` sets.
- `ModelBundle.predict(vector: FeatureVector) -> Prediction` rejects schema-version mismatch.

- [ ] **Step 1: Write the failing test**

```python
def test_grouped_split_never_places_one_book_in_both_partitions():
    split = grouped_split(sample_training_rows(), seed=7)
    assert set(split.train_books).isdisjoint(split.test_books)

def test_model_rejects_legacy_feature_schema():
    bundle = ModelBundle(model=stub_model(), schema_version=FEATURE_SCHEMA_VERSION)
    with pytest.raises(ValueError, match="schema_version"):
        bundle.predict(legacy_feature_vector())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_corpus.py tests/test_predictor.py -k 'grouped_split or legacy_feature' -v`

Expected: FAIL because the existing split/model path permits chapter leakage or silently consumes legacy vectors.

- [ ] **Step 3: Write minimal implementation**

Normalize each label as `(label - book_mean) / book_std` with a zero-variance fallback of `0.0`; stratify by platform only after grouped book assignment; log feature names and schema version in the MLflow model signature; reject mismatch before calling the estimator.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_corpus.py tests/test_predictor.py -v`

Expected: PASS with deterministic seeded grouping, platform column, and explicit model compatibility errors.

- [ ] **Step 5: Commit**

```bash
git add app/training_corpus.py app/corpus.py app/predictor.py sql/ddl.sql tests/test_corpus.py tests/test_predictor.py
git commit -m "feat: align training and model feature contracts"
```

## Task 4: Use the same vector for scoring and edit attribution

**Files:**
- Modify: `app/predictor.py`, `app/rewrite.py`
- Test: `tests/test_predictor.py`, `tests/test_rewrite.py`

**Interfaces:**
- `score_graph(graph: NarrativeGraph, boundary: int, bundle: ModelBundle) -> Prediction`.
- `attribute_edits(before: NarrativeGraph, after: NarrativeGraph, bundle: ModelBundle) -> list[FeatureAttribution]` reports feature name, before value, after value, contribution, and schema version.

- [ ] **Step 1: Write the failing test**

```python
def test_rewrite_attribution_uses_frozen_schema_and_preserves_model():
    result = attribute_edits(original_graph(), repaired_graph(), frozen_bundle())
    assert {item.feature_name for item in result} <= set(FEATURE_ORDER)
    assert all(item.schema_version == FEATURE_SCHEMA_VERSION for item in result)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_predictor.py tests/test_rewrite.py -k attribution -v`

Expected: FAIL because rewrite scoring still builds a legacy vector or reports opaque deltas.

- [ ] **Step 3: Write minimal implementation**

Build both vectors through `encode_features`; call the same `ModelBundle` instance; calculate per-feature contribution by replacing one coordinate at a time while retaining the frozen baseline; return confidence interval metadata without generating prose.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_predictor.py tests/test_rewrite.py -v`

Expected: PASS, including no-op rewrites producing zero feature deltas and unchanged model identifiers.

- [ ] **Step 5: Commit**

```bash
git add app/predictor.py app/rewrite.py tests/test_predictor.py tests/test_rewrite.py
git commit -m "feat: make scoring and attribution schema-safe"
```

## Self-review

- Spec coverage: all 11 graph features, scheduled payoff distance, fair-clue density, categorical platform encoding, grouped book split, frozen model compatibility, and rewrite attribution are covered by Tasks 1–4.
- Completeness scan: the plan contains no unfinished marker or vague implementation instruction.
- Type consistency: `FeatureVector` is the only model input; `ModelBundle` consumes it; `FeatureAttribution` reports the same `FEATURE_ORDER` and schema version.
- Verification: run `uv run --group dev pytest tests/test_feature_schema.py tests/test_features.py tests/test_corpus.py tests/test_predictor.py tests/test_rewrite.py -v`.
