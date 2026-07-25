# CanonPulse: Narrative Debt Engine

> **SUPERSEDED (2026-07-25)** by `2026-07-25-canonpulse-dual-layer-graph-design.md`.
>
> Retained for history. The product changed materially: A/B ending comparison was
> dropped in favour of whole-series analysis; the 8-episode demo grew to 220; and
> the deliberately non-predictive "Debt Health" score was replaced by a continuation
> regressor trained on public serial-fiction retention data.
>
> Note the defect this spec's plan introduced: it specified a test asserting
> `precision == 1.0` and `recall == 1.0`, so the implementation was written to
> satisfy it and the benchmark measures nothing. Corrected in the successor.

## Summary

CanonPulse is a pre-release decision system for serialized audio fiction. It turns an uploaded story and a proposed episode ending into an evidence-cited map of **narrative debt**: mysteries, relationships, emotional wounds, causal questions, and genre promises the story has opened with listeners. It compares two creator-supplied endings by showing which debts they repay, defer, renew, or default on.

It does not position factual continuity checking, ending generation, character summaries, or plot-hole detection as novel features; Pocket FM publicly offers adjacent capabilities. Those functions are supporting evidence layers.

## Product experience

1. The creator selects an original synthetic eight-episode demo series, *The Last Monsoon*, and chooses or pastes two candidate endings.
2. CanonPulse retrieves source passages, extracts or loads open debt contracts, and audits each candidate ending.
3. The Audience Court presents five bounded listener cohorts: Binge Listener, Mystery Purist, Romance Listener, Skeptic, and Late-Night Listener. Each returns a structured continue/hesitate/stop verdict, debt status, and citations.
4. A comparative verdict explains the creator-facing trade-off: debt repayment, fair deferral, new curiosity, emotional payoff, and cited risks. It suggests at most three minimal safe edits.
5. A small Mood-to-Debt Discovery tab retrieves titles from a synthetic catalogue by emotional-promise shape and explains the match using the same debt metadata.

The UI must describe the court as a **pre-release simulation**, not a validated listener-retention predictor.

## Data and AI design

Canonical data assets:

- `episodes`: original episode text, sequence, summary, and story ID.
- `story_claims`: factual claims and source excerpts; used only to ground citations and detect hard contradictions.
- `narrative_debts`: debt type, opening episode, owner characters, evidence, urgency, expected payoff window, and status.
- `candidate_endings`: the creator-provided alternatives and their audit IDs.
- `audience_cohorts`: five transparent, fixed audience preference profiles.
- `court_verdicts`: cohort verdicts, scores, and citation IDs.
- `evaluation_cases`: seeded contradictions, overdue debts, fair/unfair ending labels, and expected citations.

The primary user-facing score is `Debt Health`, broken into repayment, fair deferral, emotional payoff, and new-curiosity dimensions. A deterministic, visible aggregation produces the comparison; no percentage is labelled as real retention uplift.

Audience Court outputs use a strict structured schema: vote, debt status, fairness score, urgency score, explanation, and source claim IDs. Outputs without citations are rejected from the verdict.

## Databricks architecture

Production mode is a Databricks App backed by Delta tables and Databricks AI Search. AI Search retrieves episode evidence by story and episode metadata. The Court runs as a structured `ai_query` batch over `audience_cohorts` joined to the retrieved draft context, so Databricks performs a visible, non-trivial part of the product.

Primary inference uses a Databricks Foundation Model or governed model service selected by configuration. The direct OpenAI key is an optional local/failover provider only. MLflow tracing instruments retrieval, audit, and court functions; Unity AI Gateway inference tables and usage monitoring are enabled only when the workspace, privileges, and preview availability permit them.

Databricks Asset Bundles define the app, but catalog, schema, warehouse, model service, AI Search index, and MLflow experiment are variables. No resource IDs or credentials are hardcoded. The app uses service-principal app authorization in deployed mode and an explicit `demo` mode locally.

## Reliability and demo constraints

The demo corpus is fully original and synthetic. It contains six labelled factual contradictions, six labelled narrative-debt failures, and two labelled candidate endings. DefectLab reports measured issue precision/recall, citation-support rate, and structured-output validity. These metrics validate audit reliability; they do not validate future listener retention.

Pocket FM credentials, production story text, user telemetry, publishing, voice cloning, and real retention claims are out of scope. Deployment requires a Databricks workspace profile plus a user-approved Unity Catalog and schema; until then the local app must make its demo mode explicit.

## Acceptance criteria

- The comparison view demonstrates a different debt outcome for the two endings with cited evidence.
- The Court visibly disagrees where cohort preferences differ and never presents its result as real user data.
- DefectLab reports actual results against the labelled corpus.
- The project includes a Databricks App configuration, DAB configuration, AI Search setup workflow, and MLflow tracing/evaluation path with parameterized resources.
- The local demo works without Pocket FM or Databricks credentials; Databricks mode fails clearly rather than silently falling back.
