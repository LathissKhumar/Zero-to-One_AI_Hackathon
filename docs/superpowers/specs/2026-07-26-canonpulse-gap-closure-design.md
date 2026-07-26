# CanonPulse Gap Closure — Design

Date: 2026-07-26
Source: gap audit against "CanonPulse AI — Master Technical Specification" (see conversation), run against current `app/` tree.

## Scope

Close the gaps found in the audit, in priority order: **orphaned code → faked stubs → partial implementations**. Four items require a real LLM connection; user has confirmed: connect via **OpenAI**, key already present in `.env` as `OPENAI_API_KEY`, no model pinned yet (default `gpt-4o-mini`, override via `OPENAI_MODEL`). No Databricks credentials available in this session — Databricks-specific paths (`DatabricksExtractor`, `ai_query` cohort path) stay code-complete but unconfigured/untriggered, same as today.

`python-dotenv` will be added so `.env` loads at process start (currently nothing reads it).

## Phase 1 — Orphaned code

**1.1 Wire `app/document_ingestion.py` into the API.**
`normalize_parsed_document` exists, is tested, is never called from `main.py`. Add `POST /api/ingest/document` accepting `{parsed: <ai_parse_document JSON>, source_path, series_id, title, genre, language}`, calling `normalize_parsed_document(...)`, then feeding the resulting `SubmissionInput` into the existing `ingestion_coordinator.submit(...)`. Response includes `review_required`/`warnings` verbatim so a caller knows if episode boundaries were guessed.

**1.2 Make `IngestionCoordinator`'s extractor real.**
Today `_DefaultIngestionExtractor.extract_fast`/`extract_deep` are no-ops (`return None`) — work items flip to "complete" but no graph is ever produced or stored. Fix:
- Extend `SubmissionRepository` protocol (+ `InMemorySubmissionRepository`) with `record_extraction(job_id, episode_number, stage, result: ExtractionResult)` and `series_for(job_id) -> Series | None`, accumulating nodes/entries/payoffs/excerpts per job across episodes.
- New `_RealIngestionExtractor(fast_extractor, deep_extractor, repository)`:
  - `extract_fast` → `HeuristicExtractor` over synopsis only, confidence scaled to 0.4 (matches existing `SynopsisExtractor` convention).
  - `extract_deep` → real `LLMExtractor` (OpenAI, `gpt-4o-mini` default) over full episode body when `OPENAI_API_KEY` is set; falls back to `HeuristicExtractor` when it isn't (mirrors `_predictor()`'s "trains regardless, degrades gracefully" pattern — same honesty convention as the rest of the repo, never silently claims the LLM ran when it didn't: `ExtractionResult.backend` already carries this label).
- `main.py` constructs this via a `_deep_extractor()` factory (parallel to existing `_predictor()`), read once, cached.

## Phase 2 — Faked stubs

**2.1 Personas → real names, real optional LLM backend.**
Rename `PERSONAS` in `app/personas.py` to spec's five: Director (macro pacing/showrunner debt — was "Serial Showrunner"), Editor (continuity/chronology — was "Continuity Editor"), Critic (clue fairness/cliché — was "Mystery Architect"), Psychologist (emotional/relationship — was "Emotional Arc Editor"), Historian (lore/localization consistency — was "Localization Editor"). `id`s change too; this touches any test/fixture keyed on old ids.
Add `llm_persona_handler(persona, graph, budget)` using the same `Transport`/prompt/cache-key/backend-label machinery as `app/llm_extractor.py` (new small module `app/persona_llm.py`, reuses `_http_transport`, `cache_key`), producing a real chat-completion-backed `AgentAnnotation`. `AgentRunner(handler=llm_persona_handler)` becomes selectable; `run_writers_room` picks it when `OPENAI_API_KEY` is configured, else keeps the existing deterministic `_default_handler`. `Annotation.backend` reports which ran (`"deterministic-structured"` vs `"openai"`).

**2.2 Cohorts → spec names, add real Databricks-shaped path (unconfigured).**
Rename `COHORTS` to Binge Listeners, Casual Commuters, Lore Hardcores, Character Fans, Aggregate Health, remapping weight vectors onto the closest existing signal semantics (documented inline per cohort — e.g. Casual Commuters ≈ old "Late-Night Listener" clarity-weighted profile, Lore Hardcores ≈ old "Skeptic" consistency-weighted). `structural_reaction` (deterministic, local) stays the default and is unchanged in mechanism — only labels change. Add `databricks_cohort_reaction(...)` stub function with the `ai_query` batch shape (mirrors `DatabricksExtractor`), **not wired to any route and not called by default** — no Databricks credentials exist in this session, so this stays code-complete-but-dormant, consistent with `DatabricksExtractor`'s existing status. `/api/cohorts` keeps using the deterministic path; disclosure string unchanged.

**2.3 Regressor library — docs-only fix.**
Spec says LightGBM; code uses sklearn `GradientBoostingRegressor`, already trained/tested/calibrated. No swap — pure churn for no behavior change. Add one line to `app/predictor.py`'s module docstring noting the deliberate deviation from the spec's example and why (sklearn already integrated with the existing MLflow/calibration path; swapping libraries buys nothing here).

## Phase 3 — Partial implementations

**3.1 Surgical Node Repair — generate the replacement text.**
`RepairEngine.repair` (in `app/variants.py`) already does the hard part correctly: targets one node, requires a broken (not suspended) entry, preserves the rest of the graph, scores the delta via `_predictor().score_variant`. The one missing piece is that `replacement_summary` must currently be supplied by the caller — nothing generates it. Add `propose_repair_text(series, target_entry_id, node_id)` in `app/persona_llm.py`'s sibling module (or extend it) that calls OpenAI with a prompt scoped to just that node's summary + the obligation description it must stop contradicting, returns the replacement text plus `backend` label. `/api/repair` gets an optional variant: if `replacement_summary` is omitted from `RepairRequest`, the route generates it via this path before calling `RepairEngine.repair`; if `OPENAI_API_KEY` isn't set, the route 422s naming the missing config rather than fabricating a template (no silent fake).

**3.2 Two-Speed ingest wiring** — same work as 1.2, no separate implementation.

**3.3 Pre-Publish retention delta.**
`PrePublishReport` gains `retention_delta: float | None` and `prediction: Prediction | None`. In `main.py`'s `/api/prepublish` route (not inside `PrePublishChecker`, which stays predictor-agnostic and pure), predict on the series before vs. after the candidate episode using the existing `_predictor()` and `FeatureExtractor`, same pattern as `score_variant`. Populated only when extraction succeeded (`report.complete`); `None` otherwise, not zero.

**3.4 Narrative Debt Index (NDI).**
`DebtBoard` gains `narrative_debt_index: float` — defined as the mean `risk` across all open items on the board (0 when the board is empty), named and documented explicitly in `app/surfaces.py` so "NDI" stops being an implicit synonym for the per-item `risk` field the spec never actually names.

**3.5 Localization graph-parity check (small addition).**
`LocalizationChecker.check` currently only regex-diffs colours/numbers/temporal words/entity names between source and translated text. Add one more `LocalizationFinding(dimension="graph_parity", ...)`: run `HeuristicExtractor` over the translated text as its own single-episode row, compare the resulting node/entity count against the source episode's node's entity count; flag `warning` when they diverge. This is still heuristic (no cross-language embeddings — out of scope), but it is graph-derived rather than pure word-overlap, closing part of the "not full edge alignment" gap without new infra.

## Non-scope (explicitly deferred)

- Swapping sklearn → LightGBM (no behavior change, declined above).
- A literal 1000-agent Llama-3.1 Databricks streaming simulator (`databricks_cohort_reaction` is the code-complete stand-in; actually running it needs a Databricks workspace, not available this session).
- Full semantic/embedding-based cross-language edge alignment for localization (3.5 is a bounded, cheaper approximation).

## Testing approach

Every new LLM-calling path gets a fake `Transport` in tests (same pattern `tests/test_llm_extractor.py` already uses) — no real network calls in the test suite, matching existing convention. A single manual/integration check against the real OpenAI key happens after implementation, run explicitly, not part of `pytest`.
