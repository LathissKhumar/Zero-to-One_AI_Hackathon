# CanonPulse Domain and Dual-Layer Graph Specification

## Purpose

Turn extracted episode evidence into a versioned narrative graph and resolve
every ledger entry deterministically. The module hides graph indexing,
chronology, payoff verification, citation assembly, and boundary traversal
behind a small interface.

## Canonical model

`Series` owns immutable source versions. `Episode` belongs to one series and has
an episode number, synopsis, optional full text, writer identity, language, and
source hash. `NarrativeNode` belongs to an extraction run and carries its
perceived episode, optional normalized true-time coordinate, entities,
valence, node kind, and citation references.

`G_true` and `G_perceived` are two indexed views over the same node IDs. They
must not duplicate node content. An edge records relation type, source node,
target node, confidence, extraction run, and evidence. Supported relation types
are `supports`, `contradicts`, `plants`, `pays_off`, `depends_on`, and
`character_thread`.

`LedgerEntry` is either a contradiction or obligation. A contradiction has at
least two incompatible claim references. An obligation has an origin node,
kind, urgency, expected payoff window, owner entities, and status history.

## State machine

| Entry kind | Transition | Condition |
|---|---|---|
| contradiction | `candidate → suspended` | downstream payoff passes independent verification |
| contradiction | `candidate → broken` | no verified payoff by the review horizon |
| obligation | `candidate → outstanding` | no accepted payoff by the review horizon |
| obligation | `candidate → paid` | a payoff exists after the origin and passes obligation rules |
| outstanding | `outstanding → paid` | a later accepted payoff is added in a new run |
| any | `* → superseded` | source or extraction version is replaced; never delete history |

No state transition mutates the source episode or an earlier extraction run.

## Payoff verification

The resolver first creates candidate payoff links from extraction output. A
verifier evaluates each candidate using:

1. downstream ordering and minimum episode gap;
2. target-kind compatibility;
3. entity and thread agreement;
4. claim-specific contradiction resolution or obligation discharge;
5. cited excerpt support;
6. an independent structured verifier result with model, prompt, and evidence
   provenance.

The resolver accepts a contradiction payoff only when all deterministic checks
pass and the verifier returns `accepted`. An extractor cannot set `verified`.
Verifier failure is fail-closed: the entry remains broken and the UI explains
that protection could not be established.

## Boundary semantics

At boundary `b`, the resolver includes source and extracted nodes with
`perceived_index <= b`, entries whose origin is visible by `b`, and payoff
claims visible by `b`. A later payoff cannot protect an earlier boundary. The
full-series view may show a later protected twist; a pre-publish view must not
use it to judge an episode that predates the payoff.

## Interfaces

```text
GraphBuilder.build(extraction_result, series_version) -> NarrativeGraph
LedgerResolver.resolve(graph, horizon, verifier) -> LedgerSnapshot
LedgerResolver.resolve_entry(entry_id, horizon) -> ResolvedEntry
LedgerSnapshot.citations(entry_id) -> tuple[Citation, ...]
```

The interface is immutable from the caller's perspective. Implementations may
cache indexes, but returned graphs and snapshots are safe to retain.

## Acceptance criteria

- The same series and extraction version produce byte-stable graph indexes and
  ledger states.
- A flashback has different true-time and perceived-order positions without
  being treated as a contradiction solely because of that difference.
- A contradiction with a verified downstream payoff is `suspended`; the same
  contradiction without verification is `broken`.
- A same-episode payoff never resolves its own plant.
- Every non-paid finding includes citations that exist in the source version.
- Resolving at boundary `b` is unchanged when episodes after `b` are appended.
- Replacing an extraction run never changes historical run results.

## Tests

Use public behavior tests for graph ordering, state transitions, verifier
fail-closed behavior, citation completeness, horizon isolation, version
immutability, and the seeded 20-item manifest. Do not test private indexing
containers or exact graph library calls.
