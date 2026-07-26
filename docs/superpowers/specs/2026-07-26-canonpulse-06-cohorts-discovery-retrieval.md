# CanonPulse Cohorts, Retrieval, and Discovery Specification

## Purpose

Add bounded audience simulation and obligation-index discovery without
confusing either with real reader behavior or the continuation regressor.

## Cohort simulation

The five fixed cohorts remain transparent weight vectors over structural
features: Binge Listener, Mystery Purist, Romance Listener, Skeptic, and
Late-Night Listener. A cohort reaction contains engagement, vote, structured
reaction, feature rationale, citation IDs, model/backend metadata, and variant
metadata.

The Databricks pass is one governed query over cohort × episode rows. Original
and rewrite variants are normalized to identical input fields, randomly
assigned opaque IDs, and evaluated blind. The unblind map is retained only for
evaluation and never included in the model prompt.

## Retrieval and Vector Search

`EvidenceRepository` supports exact citation lookup and semantic search over
episode excerpts, filtered by series, language, episode range, entry type, and
source version. Databricks Vector Search is the production adapter; an
in-memory deterministic adapter supports local mode. Retrieval results always
return excerpt ID, episode, score, source hash, and matched ledger dimensions.

## Discovery

Discovery accepts an emotional or structural query such as “rainy Sunday after
heartbreak.” It ranks catalogue entries by obligation-shape dimensions rather
than claiming semantic truth. “Explain Why” returns the matched unresolved
longing, emotional payoff, pace, or clue-fairness dimensions with citations.
Discovery never exposes training rows or private source text from another
series.

## Acceptance criteria

- Cohorts produce materially different reactions when their weight vectors
  differ and identical reactions when inputs are identical.
- Blind evaluation strips variant identity from all prompt-visible fields.
- Heatmap data can be regenerated from governed stored rows.
- Retrieval is filtered by series and source version and returns citations.
- Discovery explanations name the dimensions that drove ranking and link to
  evidence.
- All audience output is labelled as simulation, not observed behavior.

## Tests

Test weight sensitivity, blind/unblind round trips, SQL parameterization,
variant leakage, heatmap aggregation, retrieval filters, deterministic local
search, explanation citations, and cross-series privacy.
