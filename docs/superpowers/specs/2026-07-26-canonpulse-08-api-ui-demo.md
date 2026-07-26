# CanonPulse API, UI, and Demo Specification

## Purpose

Present the product as a writer-facing tool while keeping every verdict,
number, caveat, and degraded state inspectable.

## API shape

Retain and version the existing endpoints:

- `GET /api/series`
- `GET /api/audit`
- `GET /api/discrimination`
- `GET /api/predict?episode=N`
- `POST /api/rewrite`

Add versioned endpoints for:

- series submission and job status;
- memory search;
- pre-publish checks;
- writer handoff;
- portfolio debt board;
- localization checks;
- cohort heatmap;
- discovery and explain-why;
- extraction/evaluation run diagnostics;
- variant and graph diffs.

Every response includes series/version identity, provenance, completeness,
citations where relevant, and an error/degraded state. Request IDs make a UI
finding traceable to logs and workspace runs.

## UI surfaces

The dashboard has these navigable views:

1. Series overview and Story Health.
2. Evidence-backed ledger and Series Memory.
3. Pre-Publish Check with candidate episode status.
4. Repair and attributed diff.
5. Handoff Sheet.
6. Showrunner Debt Board.
7. Localization Continuity.
8. Cohort heatmap with blind-evaluation disclosure.
9. Discovery with Explain Why.
10. Run diagnostics and model/data disclosure.

Loading, partial, empty, timeout, validation, and workspace-unavailable states
must be designed explicitly. The offline bundle renders the golden path when
the configured timeout is exceeded and labels it as degraded.

## Accessibility and safety

Projector legibility requires high contrast, large type, keyboard navigation,
visible focus, and non-color-only state labels. Server strings are inserted as
text nodes or escaped templates; writer-provided episode text must never be
used as raw HTML. API errors must not leak credentials or internal prompts.

## Demo choreography

The complete demo remains: load the 220-episode series; show baseline versus
protected twists and real holes; open the 171-episode citation; repair a hole
through a true variant; show frozen-model attribution and interval; show the
blind cohort heatmap; then show discovery and Explain Why. Every screen keeps
synthetic-data and no-real-reader-data disclosures visible.

## Acceptance criteria

- Existing local demo endpoints continue to work.
- Every new surface has an API response and UI state.
- No visible finding lacks a citation or provenance label.
- Workspace mode and demo mode are distinguishable.
- The golden path renders without live inference or network.
- The complete demo can be executed repeatedly with identical cached results.

## Tests

Use FastAPI contract tests for each endpoint, frontend smoke assertions for
required labels and disclosures, accessibility checks for focus/contrast
markers, XSS regression tests with hostile episode text, timeout fallback
tests, and a scripted golden-path smoke test.
