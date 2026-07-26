# CanonPulse Repair, Scrambler, and Writers Room Specification

## Purpose

Provide controlled graph edits and structured craft review without turning the
system into an unconstrained prose generator. Every variant is immutable,
diffable, attributable, and rescored through the frozen continuation model.

## Surgical Node Repair

`RepairEngine` accepts a source version, target broken entry, repair strategy,
and explicit approval policy. It may alter only the smallest node or claim set
needed to resolve the target. It returns a `Variant` containing original and
replacement excerpts, graph diff, discharged entry IDs, newly introduced
entries, citation support, and a human-review status.

It must reject edits that touch unrelated nodes, silently alter character
identity, discharge an obligation without evidence, or change source history.
The UI may propose a repair, but a writer approves it before it becomes a
variant.

## Non-linear scrambler

`Scrambler` generates presentation-order variants while preserving the true
story graph. Allowed operations include flashback insertion, reveal deferral,
parallel-thread interleaving, and unreliable-narrator framing. Each operation
must preserve:

- all `G_true` node IDs and causal edges;
- the set of claims and eventual payoffs;
- chronology constraints declared by the author;
- citation identity;
- the graph's truth-time ordering.

Only `G_perceived` and presentation metadata may change. The result includes a
machine-checkable invariant report. A failed invariant invalidates the variant
and prevents scoring.

## Micro-foreshadowing

`ForeshadowingEngine` can insert a minimal clue for a selected outstanding
obligation. It must declare target obligation, insertion episode, clue type,
text delta, expected payoff relation, and possible reader confusion. It never
inserts unreviewed prose directly into the original series.

## Writers Room

Five independent craft personas emit structured annotations, not prose:

1. Continuity Editor — contradiction and chronology risk.
2. Mystery Architect — clue fairness and reveal timing.
3. Emotional Arc Editor — unresolved relationship and emotional obligations.
4. Serial Showrunner — urgency, episode momentum, and debt portfolio.
5. Localization Editor — culture-, language-, and translation-sensitive risk.

Each annotation carries target node/entry IDs, proposed action, confidence,
rationale, citations, and disagreement metadata. Persona output cannot directly
change ledger state or model features.

## Acceptance criteria

- A repair diff changes only the named corrupted node and resolves the target
  entry when accepted.
- Original and variant predictions use the same model version.
- A scrambler changes perceived order while the true graph hash remains equal.
- Invalid temporal or causal permutations are rejected.
- Foreshadowing always names the obligation it serves and is reversible.
- Persona outputs are schema-valid, citation-backed, and independently
  attributable.
- No agent emits free-form replacement content as an implicit state change.

## Tests

Use property tests for graph invariants, golden repair fixtures, diff scope,
model freezing, round-trip scrambler checks, rejected invalid permutations,
foreshadowing reversibility, persona schema validation, and disagreement
preservation.
