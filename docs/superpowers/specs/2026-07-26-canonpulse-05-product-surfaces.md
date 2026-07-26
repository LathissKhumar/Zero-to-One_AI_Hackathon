# CanonPulse Product Surfaces Specification

## Purpose

Expose the same versioned ledger through the five writer-facing surfaces in the
canonical plan. These are read models and workflows over shared deep modules,
not five separate continuity engines.

## Series Memory

Search and browse all prior plants, claims, payoffs, character threads, and
citations. A query such as “what did we plant in episode 47?” returns source
episode, entry state at a selected horizon, payoff history, writer, and exact
excerpt. Results identify source and extraction versions.

## Pre-Publish Check

Accept a proposed episode or episode window against an existing series version.
Return new contradictions, newly opened obligations, likely payoff candidates,
overdue debt affected, continuation prediction before/after, and a blocking
severity. The check must support draft-only mode and must not mutate the
published series.

## Writer Handoff Sheet

For a selected writer and handoff boundary, show inherited open obligations,
overdue entries, recent unresolved claims, owner characters, evidence, and
recommended next actions. Writer identity comes from submission metadata, not
inferred from prose.

## Showrunner Debt Board

Aggregate obligations across multiple active series. It supports filtering by
series, writer, urgency, age, genre, and state; sorting by risk; and drilling
into citations. Aggregation never combines entries across series IDs.

## Localization Continuity Check

Accept a translated episode linked to an original episode and language. Compare
its extracted claims, entities, temporal markers, numbers, names, clue
visibility, and payoff references to the canonical ledger. Report translation
continuity findings separately from source-story findings. A translation cannot
rewrite the source ledger.

## Interfaces

```text
MemoryQuery.search(series_id, query, horizon, filters) -> MemoryResult
PrePublishChecker.check(series_version, candidate_episode) -> PublishReport
HandoffQuery.for_writer(series_id, writer_id, horizon) -> HandoffSheet
DebtBoardQuery.aggregate(series_ids, filters) -> DebtBoard
LocalizationChecker.check(source_episode, translated_episode, language) -> LocalizationReport
```

## Acceptance criteria

- All five surfaces operate on a selected series/version rather than the demo
  singleton.
- Every result links to source citations and records the horizon used.
- Pre-publish checks are non-mutating and can be rerun idempotently.
- Handoff and debt-board aggregates preserve writer and series identity.
- Localization findings distinguish translation drift from source continuity
  defects and support multiple configured languages.
- Empty, partial, and stale extraction states are explicit in each surface.

## Tests

Test query filtering, horizon behavior, writer/series isolation, draft
non-mutation, aggregation correctness, translation mismatch fixtures, citation
support, and API validation through surface interfaces.
