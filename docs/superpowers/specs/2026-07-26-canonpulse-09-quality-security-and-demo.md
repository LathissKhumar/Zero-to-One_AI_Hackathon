# CanonPulse Quality, Security, and Demo Reliability Specification

## Purpose

Make correctness claims measurable, model/data provenance explicit, and demo
failure recoverable without hiding limitations.

## Evaluation tracks

Maintain separate reports for:

1. ledger traversal on an authored graph;
2. heuristic extraction end to end;
3. configured model extraction end to end;
4. repair/scrambler invariant validity;
5. cohort blind-variant discrimination;
6. prediction held-out error and interval coverage.

The manifest is hand-authored and held out from the analyzer. Reports include
precision, recall, clean-control false-positive rate, citation support,
structured-output validity, rejection counts, and provenance. No test may
assert a narrative-quality metric equals exactly 1.0 as a required success
condition.

## Security and privacy

- Secrets come only from environment or platform secret stores.
- Source text is scoped by series, workspace identity, and authorization.
- Writer IDs and translation data are not inferred or exposed across series.
- Logs redact tokens, prompts containing protected text when configured, and
  full episode bodies by default.
- User text is escaped in UI output and bounded in request size.
- SQL values are parameterized or safely encoded; identifiers are validated
  against configured allowlists.
- Model output is treated as untrusted structured data.

## Observability

Record request ID, series/version, extraction/model/evaluation run IDs,
latency, token/cost estimates, row counts, failure class, fallback state, and
model version. Health checks distinguish application health, workspace health,
model health, and data freshness.

## Demo hardening

Precompute and validate the complete golden path. Warm configured model and
retrieval endpoints. Switch to cached offline data after the configured timeout
and announce the switch. Rehearse six complete runs with a driver, clock, and
failure observer. Never silently fabricate a missing result.

## Acceptance criteria

- All evaluation tracks produce versioned artifacts with honest labels.
- Security tests cover prompt injection in episode text, XSS, SQL injection,
  cross-series access, secret leakage, and malformed model output.
- Fallback behavior is deterministic and visibly degraded.
- Run diagnostics can explain every displayed number.
- Full local suite, static asset checks, and workspace smoke checks are green
  before a release is frozen.

## Tests

Combine unit tests at deep module interfaces, API contract tests, property
tests for graph invariants, fixture-based evaluation, static deployment checks,
security regression tests, and a manual workspace/demo checklist. Tests must
not depend on network access or real credentials unless explicitly marked as
the gated workspace integration suite.
