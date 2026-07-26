# CanonPulse Domain Context

CanonPulse is a standalone review system for serialized fiction. This file is
the domain vocabulary only; implementation decisions belong in the specs and
plans under `docs/superpowers/`.

## Core vocabulary

- **Series** — the complete serialized work being reviewed.
- **Episode** — one released or proposed unit in a series. CanonPulse never
  calls this a chapter in product-facing language.
- **Submission** — a writer's imported series, including synopsis text, full
  episode text when available, and ownership metadata.
- **Narrative node** — an extracted story event, claim, clue, emotional beat,
  or character-state change with evidence.
- **Perceived order** — the order in which listeners encounter information.
- **True time** — the chronological order in which an event occurs in the
  story world.
- **`G_true`** — the graph ordered by true time.
- **`G_perceived`** — the graph ordered by listener-facing presentation order.
- **Claim** — a proposition or story fact that can later be supported,
  contradicted, qualified, or revealed as intentionally misleading.
- **Contradiction** — two incompatible claims detected in the narrative.
- **Obligation** — a promise, question, clue, emotional need, causal setup, or
  genre expectation that the story has opened and has not yet discharged.
- **Payoff** — a later node that discharges an obligation or explains a
  contradiction.
- **Payoff verification** — independent evidence that a proposed payoff really
  addresses the target; an extractor's assertion is not verification.
- **Ledger entry** — a contradiction or obligation before resolution.
- **Ledger state** — `suspended` (contradiction protected by a verified later
  payoff), `broken` (unrepaired contradiction), `outstanding` (unpaid
  obligation), or `paid` (obligation discharged).
- **Narrative debt** — the accumulated risk represented by outstanding and
  broken ledger entries.
- **Boundary** — the point immediately after an episode. Features and
  predictions are always evaluated at a boundary.
- **Structural feature** — a numeric property derived from the graph and
  ledger. It contains no prose.
- **Continuation prediction** — an estimate of next-episode continuation at a
  boundary. It is a model output, not a claim about real audience behavior.
- **Cohort** — a transparent simulated listener profile with a documented
  structural preference vector. A cohort is not a real user or panel.
- **Writers Room persona** — a craft-review role that emits structured graph
  annotations, not replacement prose.
- **Citation** — an episode excerpt that supports a ledger verdict, feature,
  or explanation.
- **Variant** — an original or proposed rewrite representation. Variant labels
  must be hidden during blind cohort evaluation.
- **Extraction run** — one versioned conversion of episode input into nodes,
  entries, payoffs, excerpts, and provenance.
- **Translation** — a localized episode representation checked against the
  same language-independent ledger.

## Invariants

1. The predictor consumes structural features only; it never receives prose,
   summaries, citations, or model-generated explanations.
2. A boundary never reads an episode after itself.
3. An unverified payoff never protects a contradiction.
4. Every user-visible finding and explanation has at least one reachable
   citation, or is explicitly marked as unsupported and withheld from the
   product view.
5. Synthetic demo data, synthetic cohort reactions, and synthetic training
   labels are always disclosed as synthetic.
6. A rewrite changes a variant graph, not the original series or its ledger.
7. A blind evaluator cannot infer variant origin from identifiers, ordering,
   metadata, or prompt text.
8. Every inference run has a backend, model version, input version, and cost /
   latency record.
9. Series, writer, and translation identity are explicit dimensions; no
   endpoint silently operates on a process-global demo series in production
   mode.
