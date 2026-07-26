# CanonPulse Complete Implementation Plan

> This plan completes every item in `canonpulse-16h-plan.md`, including the
> items previously marked as cut-gate or deliberately deferred. It is written
> for task-by-task implementation with tests before production code.

## Goal

Turn the current local demo into a complete, versioned, platform-independent
CanonPulse product: ingest a series, build and verify its dual-layer graph,
resolve narrative debt, score structural continuation, evaluate real repairs,
serve the five writer surfaces, run cohorts and discovery, and deploy the
governed Databricks path with an offline fallback.

## Global constraints

- Preserve the vocabulary and invariants in `CONTEXT.md`.
- Keep the predictor prose-blind and every boundary causal.
- Never let an unverified payoff protect a contradiction.
- Keep source, extraction, graph, ledger, model, variant, and evaluation
  versions explicit.
- Preserve the synthetic-data disclosures until real licensed data exists.
- Prefer deep modules with small interfaces and adapters at explicit seams.
- Write a failing external-behavior test before implementation for every task.
- No task is complete because a schema, SQL file, or adapter merely exists; its
  acceptance test must exercise the behavior.

## Dependency order

```text
CP-001 → CP-002 → CP-003 → CP-004 → CP-005
                 ↘ CP-006 → CP-007 → CP-008 → CP-009 → CP-010
CP-003 → CP-011 → CP-012 → CP-013 → CP-014
CP-003 → CP-015 → CP-016 → CP-017 → CP-018 → CP-019
CP-005 → CP-020 → CP-021
CP-001..CP-021 → CP-022 → CP-023 → CP-024 → CP-025 → CP-026 → CP-027 → CP-028
```

## Phase 1 — Domain and graph foundation

### CP-001: Establish the domain model and versioned graph

**Spec:** `docs/superpowers/specs/2026-07-26-canonpulse-01-domain-and-graph.md`

**Seam:** `GraphBuilder.build()` and immutable `NarrativeGraph`.

**Files:** extend `app/narrative_models.py`; add graph/version modules and
`tests/test_graph_model.py`; update `CONTEXT.md` only when vocabulary changes.

**Steps:**

- [ ] Add source, extraction, graph, edge, citation, variant, language, and
  writer identifiers.
- [ ] Represent `G_true` and `G_perceived` as indexed views over shared nodes.
- [ ] Validate node coordinates, edge references, source hashes, and episode
  ranges at construction.
- [ ] Add stable graph hashing for invariant checks and cache keys.
- [ ] Add migration/loading support for the current demo JSON fixture.
- [ ] Write tests for flashbacks, missing true time, duplicate IDs, dangling
  edges, stable hashes, and source-version isolation.

**Acceptance:** the current 220-episode fixture loads into the new graph
without changing its authored ledger result; graph views contain no duplicated
node content; invalid graphs fail before ledger resolution.

### CP-002: Build the boundary projector

**Spec:** domain spec and training spec.

**Seam:** `BoundaryProjector.project(graph, episode) -> BoundarySnapshot`.

**Files:** refactor `app/features.py`; extend `app/narrative_models.py`; add
`tests/test_boundary_projector.py`.

**Steps:**

- [ ] Define visible nodes, claims, obligations, payoff commitments, and
  citations at a boundary.
- [ ] Enforce no-lookahead for entries, nodes, scheduled payoffs, and
  translations.
- [ ] Return completeness and extraction-confidence metadata with the
  snapshot.
- [ ] Replace implicit process-global series reads with an explicit series
  version argument.

**Acceptance:** mutating any episode after boundary `b` cannot change the
boundary snapshot or its feature inputs.

### CP-003: Implement independent payoff verification and ledger resolution

**Spec:** domain spec.

**Seam:** `PayoffVerifier.verify(candidate, graph, evidence) -> Verification`;
`LedgerResolver.resolve(snapshot) -> LedgerSnapshot`.

**Files:** extend `app/ledger.py`, add verifier adapters and
`tests/test_payoff_verifier.py`; preserve `tests/test_ledger.py` behavior.

**Steps:**

- [ ] Separate extractor candidate links from verifier decisions.
- [ ] Implement deterministic checks for ordering, kind compatibility, entity
  agreement, claim resolution, and citation support.
- [ ] Add a governed structured verifier adapter with fail-closed behavior.
- [ ] Record verifier model, prompt version, evidence IDs, and decision reason.
- [ ] Resolve contradictions to suspended only after accepted verification.
- [ ] Add horizon-aware resolution for pre-publish and historical views.

**Acceptance:** the same candidate link is broken without verification and
suspended only with accepted verification; promises retain their distinct paid
behavior; all states have citations or an explicit withheld status.

## Phase 2 — Ingestion and extraction

### CP-004: Implement submission storage and two-speed ingest

**Spec:** `02-ingestion-and-extraction.md`.

**Seam:** `SeriesRepository` and `IngestCoordinator`.

**Files:** add repository/coordinator modules; extend `app/series_loader.py`;
add API schemas; add `tests/test_ingestion.py` and repository fakes.

**Steps:**

- [ ] Accept JSON, newline-delimited episode records, and structured upload
  metadata with size and encoding validation.
- [ ] Persist series/version/episode/source-hash records idempotently.
- [ ] Run a fast synopsis pass and publish a partial ledger job result.
- [ ] Queue deep episode extraction with resumable per-episode status.
- [ ] Atomically promote a complete validated extraction run.
- [ ] Add cancellation, retry, duplicate submission, and stale-run behavior.

**Acceptance:** a new 220-episode submission is usable before deep extraction
completes; a failed episode does not erase successful rows; production mode
never falls back to the committed demo series.

### CP-005: Complete the extraction adapter family

**Spec:** extraction spec.

**Seam:** `ExtractionAdapter.extract(batch)`.

**Files:** refactor `app/extraction.py`, `app/llm_extractor.py`, and
`app/heuristic_extractor.py`; add synopsis and Databricks adapters; extend
`tests/test_extraction.py` and `tests/test_llm_extractor.py`.

**Steps:**

- [ ] Unify local, heuristic, synopsis, and Databricks structured output under
  the canonical extraction result.
- [ ] Bind source version and episode hashes to every result.
- [ ] Add bounded retries and row-level failure records.
- [ ] Ensure all extracted payoff links force `verified=False`.
- [ ] Wire the configured Databricks adapter into workspace application mode.
- [ ] Run the model measurement script against credentials only when explicitly
  requested; never fabricate a cache or result.

**Acceptance:** `/api/discrimination` can report backend and extraction-run
metadata; the workspace path uses Databricks Foundation Model APIs; local tests
remain offline and deterministic.

## Phase 3 — Training, evaluation, and prediction

### CP-006: Add real corpus adapter contracts

**Spec:** `03-training-and-prediction.md`.

**Seam:** `RetentionCorpusAdapter.load(source_config) -> TrainingRows`.

**Files:** extend `app/corpus.py`; add source adapter modules and
`tests/test_corpus_adapters.py`; add opt-in scripts under `scripts/`.

**Steps:**

- [ ] Define schemas for arXiv, Qidian, and Royal Road native labels.
- [ ] Add licensing, provenance, download checksum, and source-version fields.
- [ ] Normalize labels within book and preserve platform identity.
- [ ] Add a deterministic synthetic adapter as the default test adapter.
- [ ] Fail clearly when network or license configuration is absent.

**Acceptance:** each source can produce normalized rows when configured, and no
source is silently represented by synthetic labels in a real-data report.

### CP-007: Align the feature contract with the canonical plan

**Spec:** training spec.

**Seam:** `FeatureProjector.project(boundary) -> FeatureVector`.

**Files:** update `app/features.py`, `app/predictor.py`,
`app/narrative_models.py`, `sql/ddl.sql`, and focused feature tests.

**Steps:**

- [ ] Add known scheduled-payoff distance, fair-clue density, and the complete
  canonical feature set.
- [ ] Decide and document categorical platform encoding at training time only.
- [ ] Remove any feature that reads future realized outcomes.
- [ ] Version the vector schema and assert key ordering at the seam.
- [ ] Add feature explanations that reference graph dimensions, not prose.

**Acceptance:** the active vector matches the feature specification exactly;
SQL, model, API, and tests use the same schema version.

### CP-008: Train, calibrate, and freeze the continuation model

**Spec:** training spec.

**Seam:** `ContinuationModel`.

**Files:** refactor `app/predictor.py`; add model artifact/version modules and
`tests/test_predictor_contract.py`.

**Steps:**

- [ ] Train on normalized rows with grouped book split.
- [ ] Report held-out MAE, per-platform metrics, and residual quantiles.
- [ ] Calibrate displayed rates only from the configured training distribution.
- [ ] Return named intervals, clamping, provenance, and model version.
- [ ] Add immutable model handles for original/variant comparisons.

**Acceptance:** two variant scores use the identical frozen model artifact;
confidence intervals are bounded and explain their method; synthetic mode is
never described as observed retention.

### CP-009: Build the evaluation harness

**Spec:** quality spec.

**Seam:** `EvaluationRunner.run(series_version, manifest, extractor)`.

**Files:** extend `app/evaluation.py` and `app/manifest.py`; add evaluation
fixtures and tests.

**Steps:**

- [ ] Keep authored-graph and end-to-end extraction metrics separate.
- [ ] Implement stable one-to-one matching with content and position gates.
- [ ] Report holes caught, twists protected, clean-control FPR, citations,
  rejection counts, and verifier coverage.
- [ ] Add model-extractor and heuristic-extractor report labels.
- [ ] Prevent answer-key leakage from summaries, prompts, or evaluator joins.

**Acceptance:** every metric can fail for a bad extractor, the manifest is not
passed to the analyzer, and the UI does not present traversal accuracy as
extraction quality.

### CP-010: Log governed training and evaluation to MLflow

**Spec:** training and Databricks specs.

**Seam:** `RunLogger` adapter.

**Files:** extend `app/predictor.py`; add `app/observability.py`; update SQL
evaluation tables and tests.

**Steps:**

- [ ] Log model artifact, feature schema, source versions, split strategy,
  held-out metrics, evaluation report, and cost/latency.
- [ ] Link MLflow run IDs into Delta evaluation rows and API diagnostics.
- [ ] Use local file-backed MLflow only in explicitly local mode.
- [ ] Use workspace MLflow in governed mode and fail visibly when unavailable.

**Acceptance:** a reviewer can trace a prediction to its model run and input
version without reading application logs or trusting a hardcoded number.

## Phase 4 — Variants and graph agents

### CP-011: Implement surgical node repair and counterfactual scoring

**Spec:** `04-repair-and-graph-agents.md`.

**Seam:** `RepairEngine.propose/apply` and `ContinuationModel.score_variant`.

**Files:** replace the current attribution-only behavior in `app/rewrite.py`;
add variant models, API schemas, and repair tests.

**Steps:**

- [ ] Accept target entry plus candidate node edit, not a caller-supplied
  total delta.
- [ ] Generate or accept a diff-preserving replacement with human approval.
- [ ] Re-extract only the changed node and affected edges.
- [ ] Re-resolve ledger and project features at affected boundaries.
- [ ] Score original and variant through the same frozen model.
- [ ] Attribute movement to changed structural features and report remainder.

**Acceptance:** a real hole repair changes the variant graph, leaves the
original untouched, shows a prose diff, discharges the named entry, and yields
server-computed counterfactual movement.

### CP-012: Implement the non-linear scrambler

**Spec:** repair/graph-agents spec.

**Seam:** `Scrambler.generate(graph, constraints) -> Variant`.

**Files:** add `app/scrambler.py`, graph invariant checks, and tests.

**Steps:**

- [ ] Support flashbacks, withheld reveals, parallel-thread interleaving, and
  unreliable-narrator framing.
- [ ] Preserve `G_true` hash and causal edge constraints.
- [ ] Rebuild `G_perceived`, boundary indices, and citations.
- [ ] Reject cycles and impossible chronology.
- [ ] Compare continuation and fairness features before/after scrambling.

**Acceptance:** every accepted scrambler variant changes only presentation
order; invalid variants are rejected with a machine-readable reason.

### CP-013: Implement micro-foreshadowing injection

**Spec:** repair/graph-agents spec.

**Seam:** `ForeshadowingEngine.propose(obligation, placement) -> Proposal`.

**Files:** add `app/foreshadowing.py`, UI approval flow, and tests.

**Steps:**

- [ ] Generate minimal clue proposals tied to one obligation.
- [ ] Check placement, continuity, spoiler risk, and citation support.
- [ ] Show exact text and graph diff before approval.
- [ ] Apply only as a variant and rescore after approval.
- [ ] Allow rejection and rollback without changing source history.

**Acceptance:** no clue is silently inserted; each proposal names its target,
expected payoff, evidence, and structural feature impact.

### CP-014: Implement the five Writers Room personas

**Spec:** repair/graph-agents spec.

**Seam:** `WritersRoom.review(graph_snapshot, persona_set) -> AnnotationSet`.

**Files:** add persona schemas/prompts/adapter; add UI annotation view and
tests.

**Steps:**

- [ ] Implement Continuity, Mystery, Emotional Arc, Showrunner, and
  Localization personas.
- [ ] Require structured node/entry targets, citations, confidence, and
  proposed action.
- [ ] Run personas independently and preserve disagreements.
- [ ] Prevent annotations from mutating ledger state or model input.
- [ ] Add budget, timeout, and partial-persona behavior.

**Acceptance:** five distinct structured reviews can be shown for one graph;
none produces an uncited state change or free-form hidden rewrite.

## Phase 5 — Writer and showrunner surfaces

### CP-015: Implement Series Memory

**Spec:** `05-product-surfaces.md`.

**Seam:** `MemoryQuery`.

**Files:** add query/read-model module, endpoint, UI view, and tests.

**Steps:**

- [ ] Support episode, character, obligation, claim, and citation queries.
- [ ] Support historical horizons and extraction-version selection.
- [ ] Return exact source excerpts and current state.
- [ ] Add pagination and series/version authorization.

**Acceptance:** “what did we plant in episode 47?” returns the correct entry,
status history, payoff, and citation without reading future data for a chosen
horizon.

### CP-016: Implement Pre-Publish Check

**Spec:** product-surfaces spec.

**Seam:** `PrePublishChecker`.

**Files:** add candidate-episode pipeline, endpoint, UI, and tests.

**Steps:**

- [ ] Analyze candidate text against the selected published version.
- [ ] Show new contradictions, obligations, payoff candidates, overdue debt,
  and prediction delta.
- [ ] Keep draft results isolated from published state.
- [ ] Support partial extraction and explicit confidence.

**Acceptance:** a candidate episode can be checked, revised, and checked again
without mutating the source series or prior audit.

### CP-017: Implement Writer Handoff Sheet

**Spec:** product-surfaces spec.

**Seam:** `HandoffQuery`.

**Files:** add writer metadata/read model, endpoint, UI, and tests.

**Steps:**

- [ ] Group open and overdue entries by inherited writer and current owner.
- [ ] Include evidence, last touched episode, urgency, and suggested action.
- [ ] Support handoff boundary and writer filters.
- [ ] Export a stable printable/shareable sheet with source version.

**Acceptance:** an incoming writer can see inherited debt without access to a
different series or unrelated writer's private drafts.

### CP-018: Implement Showrunner Debt Board

**Spec:** product-surfaces spec.

**Seam:** `DebtBoardQuery`.

**Files:** add portfolio aggregation module, endpoint, UI, and tests.

**Steps:**

- [ ] Aggregate multiple active series by urgency, age, overdue state, and
  broken count.
- [ ] Rank risk deterministically and link each row to evidence.
- [ ] Add series-level drilldown and filtering.
- [ ] Ensure no cross-series entry joins.

**Acceptance:** portfolio risk is available without loading every series into a
single in-memory singleton and every aggregate is explainable.

### CP-019: Implement Localization Continuity Check

**Spec:** product-surfaces spec.

**Seam:** `LocalizationChecker`.

**Files:** add translation models/extractor, endpoint, UI, and multilingual
fixtures/tests.

**Steps:**

- [ ] Link translation episodes to canonical source episodes and language.
- [ ] Compare claims, names, numbers, temporal markers, clue visibility, and
  payoff references.
- [ ] Separate translation findings from source-story findings.
- [ ] Support language-aware extraction adapters and fallback status.

**Acceptance:** a translation inconsistency is cited to both source and
translated text and never changes the source ledger.

## Phase 6 — Audience and discovery

### CP-020: Serve cohorts and the blind heatmap

**Spec:** `06-cohorts-discovery-retrieval.md`.

**Seam:** `CohortRunner.run(batch, blind=True)`.

**Files:** extend `app/cohorts.py`, add API/read model/UI, revise
`sql/cohort_reactions.sql`, and tests.

**Steps:**

- [ ] Make structural weights and prompt context consistent.
- [ ] Generate opaque, randomized variant rows before inference.
- [ ] Run the cohort × episode batch through governed `ai_query`.
- [ ] Store citation IDs, reactions, variant-blind marker, and run metadata.
- [ ] Render divergence and episode heatmap with simulation disclosure.

**Acceptance:** the five cohorts are visible in the product, the evaluation
cannot infer variant identity, and all heatmap cells are traceable to stored
rows and citations.

### CP-021: Implement Vector Search and obligation discovery

**Spec:** cohorts/discovery/retrieval spec.

**Seam:** `EvidenceRepository.search()` and `DiscoveryQuery.search()`.

**Files:** add retrieval adapter/index job, discovery endpoint/UI, SQL/index
assets, and tests.

**Steps:**

- [ ] Create and populate a parameterized Vector Search index over excerpts.
- [ ] Add deterministic local retrieval fallback.
- [ ] Filter every query by series, source version, language, and permissions.
- [ ] Rank mood queries by obligation-shape dimensions.
- [ ] Return Explain Why dimensions and citations.

**Acceptance:** retrieval works in workspace and local modes; discovery never
returns uncited or cross-series content.

## Phase 7 — Databricks and deployment

### CP-022: Complete Unity Catalog schema and idempotent loader

**Spec:** `07-databricks-operations.md`.

**Files:** revise `sql/ddl.sql`, `scripts/load_databricks.py`, bundle tests,
and add migration/version tables.

**Steps:**

- [ ] Add source/extraction/variant/language/run dimensions to tables.
- [ ] Add constraints, comments, and lineage columns.
- [ ] Make loader safe for rerun and partial failure.
- [ ] Load demo series, manifest, cohorts, and initial source embeddings.

**Acceptance:** schema and loader pass an integration run in a disposable
schema, and reruns converge without duplicate rows.

### CP-023: Deploy and exercise the governed workspace path

**Spec:** Databricks operations spec.

**Files:** update `databricks.yml`, `resources/`, `app.yaml`, scripts, and
deployment documentation.

**Steps:**

- [ ] Parameterize catalog, schema, warehouse, model endpoint, Vector Search,
  and MLflow experiment.
- [ ] Deploy the Databricks App and health endpoint.
- [ ] Run batched extraction, feature materialization, cohort query, and model
  logging in a workspace.
- [ ] Wire workspace configuration into application adapters.
- [ ] Verify Unity Catalog lineage and MLflow run linkage.

**Acceptance:** a workspace smoke test proves the sponsor-critical path rather
than only static SQL presence; configuration errors are explicit.

## Phase 8 — API, UI, safety, and reliability

### CP-024: Version the complete API surface

**Spec:** `08-api-ui-demo.md`.

**Files:** refactor `app/main.py`; add request/response modules and API tests.

**Steps:**

- [ ] Keep existing endpoints backward-compatible or version them explicitly.
- [ ] Add submission jobs, memory, pre-publish, handoff, debt board,
  localization, cohorts, discovery, variants, and diagnostics routes.
- [ ] Add request IDs, series/version selection, pagination, and auth context.
- [ ] Return structured partial, degraded, and validation states.

**Acceptance:** every planned product surface has a tested endpoint; no route
implicitly reads the demo singleton in workspace mode.

### CP-025: Build the complete frontend

**Spec:** API/UI spec.

**Files:** extend `app/static/index.html`, `app/static/app.js`,
`app/static/styles.css`; add frontend smoke tests.

**Steps:**

- [ ] Add navigation and views for all five writer surfaces, repair, cohorts,
  discovery, and run diagnostics.
- [ ] Preserve citation drawer, disclosures, error states, and degraded labels.
- [ ] Replace unsafe raw HTML insertion with escaped rendering.
- [ ] Add keyboard, focus, contrast, and projector-legibility checks.

**Acceptance:** the UI can complete the end-to-end demo and each feature has a
visible loading, empty, error, and partial state.

### CP-026: Add security and abuse controls

**Spec:** `09-quality-security-and-demo.md`.

**Files:** add auth/policy, input validation, escaping, redaction, and security
tests.

**Steps:**

- [ ] Scope all reads/writes by authenticated series access.
- [ ] Escape source text and reject oversized/malformed inputs.
- [ ] Redact secrets and protected text in logs.
- [ ] Treat model output and episode text as untrusted prompt content.
- [ ] Validate SQL identifiers and parameterize values.

**Acceptance:** hostile episode text cannot execute HTML/JS; one series cannot
read another; secrets do not appear in API errors, caches, or logs.

### CP-027: Complete offline bundle and observability

**Spec:** quality and Databricks specs.

**Files:** extend `app/demo_mode.py`, add `app/observability.py`, cached data
manifests, health endpoints, and tests.

**Steps:**

- [ ] Precompute the full golden path with source/model/run metadata.
- [ ] Add bounded timeouts and explicit degraded responses.
- [ ] Record request, run, model, latency, rejection, cost, and fallback data.
- [ ] Add health checks for app, workspace, model, retrieval, and freshness.

**Acceptance:** the entire demo renders offline with zero live inference and
every degraded result says why it degraded.

### CP-028: Run the final quality gates and rehearsal

**Spec:** quality spec.

**Files:** extend test suite, CI/local scripts, README/runbook, and release
checklist.

**Steps:**

- [ ] Run compile, full pytest, API smoke, asset checks, and security tests.
- [ ] Run evaluation tracks and archive reports/artifacts.
- [ ] Run the gated Databricks workspace smoke test.
- [ ] Execute six complete demo rehearsals and record timing/failure notes.
- [ ] Freeze the golden path and prohibit feature changes during rehearsal.

**Acceptance:** all required gates pass, limitations are documented, no
unverified metric appears as a product claim, and the demo can be driven from
the runbook without manual data repair.

## Plan self-review

### Every canonical feature is covered

The coverage matrix in `docs/superpowers/specs/2026-07-26-canonpulse-complete-scope.md`
maps every surface, architecture item, and deferred cut-gate item to one or
more tasks above. In particular, the formerly deferred non-linear scrambler,
micro-foreshadowing, Writers Room personas, Vector Search, and discovery
surface are CP-012, CP-013, CP-014, CP-021, and CP-021 respectively.

### No hidden implementation seam

All model calls pass through extraction, verifier, cohort, or observability
adapters. All persistence passes through repository/read-model seams. HTTP and
frontend code do not implement ledger rules.

### No silent quality downgrade

The plan keeps separate authored-graph, heuristic, and model-extraction
metrics; requires citations and provenance; and rejects unverified payoff
protection. The current synthetic fallback remains useful for development but
cannot be mistaken for completed real-data support.

### Completion evidence

For each task, attach tests, a short acceptance report, and (for workspace
tasks) run IDs. The final release checklist is not complete until the code,
specifications, test results, and deployment evidence agree.
