# CanonPulse: Dual-Layer Graph Narrative Engine

**Status:** Active. Supersedes `2026-07-25-canonpulse-narrative-debt-design.md`.
**Execution schedule:** `canonpulse-16h-plan.md` (repo root).
**Build window:** 16 hours, 3 people. **Judges:** Pocket FM · OpenAI · Databricks.

---

## Summary

CanonPulse is a standalone, platform-independent review system for serialized fiction. A writer submits a full series — up to 300 episodes, roughly half a million words — and CanonPulse answers three questions with cited evidence:

1. **What is actually broken?** Distinguishing accidental contradictions from intentional twists.
2. **What does the story still owe its listeners?** Open obligations, ranked by how overdue they are.
3. **Will listeners keep going?** Predicted next-episode continuation, with the specific structural reasons.

It is not a writing assistant. It is a decision system that runs before submission or before acquisition.

## Problem and positioning

Serialized fiction runs 200–500+ episodes, written by rotating teams, on a release treadmill. No human remembers what episode 47 planted by the time they write episode 312.

Existing AI writing assistants are episode-local and platform-captive. Pocket FM's CoPilot ships logic checks, cliffhanger suggestions, character bios, and localization — all operating on the episode in front of you. Nobody owns **series-lifetime obligation state**.

> Other tools help you write the next episode. CanonPulse protects the 300 you already shipped.

**Two users, one engine.** The writer preparing a submission; the acquisitions reviewer receiving them. Platforms get far more submissions than anyone can read, so contract decisions are made by skimming the first few episodes and gambling. Writers pay little; platforms pay a lot. Pitch the writer surface, monetize the reviewer surface.

**Why scale is the moat.** At ~1M tokens, "just paste it into a long-context model" fails on three counts: cost per revision, attention degradation across the span, and the need for persistent structured state that can be queried and diffed rather than regenerated. This is also why Databricks is load-bearing rather than decorative — 300-episode extraction is one batched `ai_query`, not 300 sequential calls.

## Core design: one ledger, two graphs, three states

Two graphs over the same extracted nodes:

- **`G_true`** — chronological story-time. When events actually happen.
- **`G_perceived`** — presentation order. When the listener learns of them.

Their divergence is the signal. A flashback, an unreliable narrator, or a withheld reveal all displace a node between the two graphs.

Every discrepancy resolves into exactly one state via the **backward causal payoff test** — before flagging anything, search downstream for a node that acknowledges it:

| State | Condition | Product behavior |
|---|---|---|
| **Suspended** | Contradiction, payoff exists downstream | **Protect.** Intentional twist. |
| **Broken** | Contradiction, no payoff anywhere | **Repair.** Real plot hole. |
| **Paid** | Promise, payoff exists | Closed. |
| **Outstanding** | Promise, no payoff yet | **Warn**, flagged overdue past an urgency-scaled grace window. |

This is the differentiator. Every consistency checker on the market over-flags intentional non-linearity, which is why writers ignore them. The gap between what a naive checker reports and what CanonPulse reports **is the product**, and it is visible in a single side-by-side screen.

Resolution is deterministic graph traversal. Extraction upstream uses a model; the verdict does not. The same series always yields the same result, and a judge can argue with the rule rather than being asked to trust a black box.

## Architecture

```
SERIES INGEST — writer's submission, up to 300 episodes
   two-speed: synopsis pass → usable ledger in minutes
              deep extraction backfills per episode
        │
        ▼
EXTRACTION — one batched ai_query over Delta episode rows
   nodes · entities · claims · obligations · payoff links · valence
        │
        ▼
DUAL-LAYER GRAPH  ──►  G_true (chronological)
                  └──►  G_perceived (presentation)
        │
        ▼
LEDGER TRAVERSAL — deterministic, cited
   suspended · broken · paid · outstanding
        │
        ├──► WRITERS ROOM — 5 LLM personas emitting graph annotations
        ├──► NON-LINEAR SCRAMBLER — edits G_perceived, G_true invariant
        └──► FEATURE VECTOR (structural only)
                   │
                   ▼
        CONTINUATION REGRESSOR — trained on public serial-fiction retention
                   │
                   ▼
        PREDICTION ± CI per boundary
                   │
                   ▼
        REWRITE → recompute → SAME FROZEN MODEL → Δ with per-edit attribution
```

### Components

Each is independently testable with a narrow interface.

| Module | Responsibility | Depends on |
|---|---|---|
| `app/narrative_models.py` | Domain types: nodes, entries, payoff links, features | — |
| `app/ledger.py` | Payoff test, state resolution, citations, summary counts | models |
| `app/features.py` | Boundary feature extraction | ledger, models |
| `app/extraction.py` | Batched `ai_query` → graph. The only LLM path into the ledger | models |
| `app/predictor.py` | Regressor training + serving client | features |
| `app/cohorts.py` | Cohort × episode reactions via one `ai_query` | ledger |
| `app/rewrite.py` | Surgical node repair + per-edit attribution | ledger, predictor |
| `app/main.py` | HTTP handlers. Invoke modules; hold no logic | all |

`app/engine.py` (the A/B `NarrativeDebtEngine`) is superseded and will be removed.

## Two non-negotiable invariants

These exist because the system's central credibility risk is a model grading its own output.

**1. The predictor never sees prose.** Features are structural only. A rewrite cannot improve the score by sounding better — only by changing structure: closing an obligation, raising urgency, shortening the gap to a payoff. The rewriter is therefore physically incapable of flattering itself. **No text-derived feature may ever be added to `BoundaryFeatures`.**

**2. No lookahead.** Every feature at boundary *b* uses only information available at or before *b*. A feature consulting later episodes inflates offline metrics and collapses in production. This is why payoff *distance* was rejected in favour of obligation *age* — at boundary *b* you cannot know when an obligation eventually gets paid.

Supporting control: **cohort evaluation is blind.** Version labels stripped, order randomized. Unblinded rows are not reportable as evidence.

## Data flow and storage

Unity Catalog + Delta throughout (`sql/ddl.sql`). Three streams, deliberately separate:

| Stream | Source | Surfaced to user? |
|---|---|---|
| Product input | The writer's submission | Yes |
| Demo asset | *The Last Monsoon*, 220 episodes, team-authored | Yes |
| Training data | arXiv / Qidian / Royal Road retention corpora | **Never** — model weights only |

Conflating these produces an incoherent pitch. Only the training stream needs public data.

**Training target.** Three sources with incompatible label scales, so the target is z-scored within each book, with `platform` as a categorical absorbing residual offset. **Split grouped by `book_id`, never by chapter** — chapters from one book on both sides of the split is leakage.

Lineage matters as a demo asset, not just hygiene: every warning traces through Unity Catalog back to the exact episode text justifying it.

## Ground truth and evaluation

**The superseded spec's benchmark was circular by construction.** Its plan specified a test asserting `precision == 1.0` and `recall == 1.0`; the implementation was then written to satisfy it, so `run_benchmark` detects a case exactly when the case is labelled detectable. It measures nothing. This is corrected at the spec level:

- **The defect manifest is authored by hand, before generation**, and withheld from the analyzer. If a model both plants the defects and grades detection, the resulting metric is meaningless.
- Generation is conditioned on the manifest via a **different prompt path** than analysis.
- 20 labelled items: 6 accidental holes, 5 intentional twists, 6 outstanding obligations (3 overdue), 3 clean controls.
- Reported: precision, recall, **false-positive rate on clean controls**, and the baseline checker's flag count for comparison. No metric may be asserted equal to 1.0 in any test.

Held-out MAE for the regressor is reported on unseen books. Every prediction carries error bars.

## Databricks architecture

Depth over breadth. Four primitives fully landed beats ten name-dropped.

| Primitive | Role | Why no substitute |
|---|---|---|
| **Delta + Unity Catalog** | Ledger, graph, features, lineage | Warning-to-source-text lineage is a demo artifact |
| **`ai_query`** | 300-episode extraction; entire cohort simulation as one SQL statement | Sequential API calls cannot do 1,100 rows in one governed statement |
| **Vector Search** | Payoff and evidence retrieval across the series | — |
| **MLflow** | Training runs, held-out MAE, discrimination precision/recall, traces | The credibility artifact |

**Runtime exclusivity:** 100% of product inference runs on Databricks Foundation Model APIs, which serve OpenAI GPT-class models. Both the OpenAI and Databricks judges see their platform load-bearing. The $100 direct OpenAI key is cold failover only; target is zero ungoverned inference calls during the demo. Verify current model availability and retirement dates before assigning any model.

All resources parameterized — catalog, schema, warehouse, model endpoint, index, experiment. No hardcoded IDs or credentials.

## Error handling and demo reliability

| Failure | Mitigation | Trigger |
|---|---|---|
| Endpoint cold start | Pre-warm all endpoints before the slot | Scheduled, pre-demo |
| Any inference >5s | Switch to precomputed golden path | Automatic |
| Network loss | Offline bundle renders full demo from cached Delta reads | Manual |
| Hallucinated payoff link | `verified` flag gates protection | Always on |
| Extraction returns malformed JSON | Reject row, log, continue; partial graph degrades verdict rather than breaking it | Per row |

**An unverified payoff link must never protect a contradiction.** That failure silently suppresses a real defect — the worst error this system can make.

## Testing strategy

- **Ledger:** unit tests per state transition, including the boundary case where a payoff lands in the same episode as its claim (rejected, `MIN_PAYOFF_GAP`).
- **Features:** property test asserting no feature at boundary *b* changes when episodes after *b* are mutated. This is the executable form of the no-lookahead invariant.
- **Discrimination:** measured against the manifest. Assertions bound results (`> 0.7`), never fix them at 1.0.
- **API:** handler tests confirming logic lives in modules, not handlers.
- **Databricks assets:** parameterization and `ai_query` presence, no secrets.

## Out of scope

Real platform telemetry. Publishing integration. Voice synthesis or cloning. Audio production. Validated retention claims on real listener data. Pocket FM credentials. Multi-season ingestion at production scale.

## Acceptance criteria

1. Side-by-side screen shows the baseline checker over-flagging while CanonPulse separates real holes from protected twists, with a cited payoff spanning 150+ episodes.
2. Discrimination precision/recall measured against the hand-authored manifest and logged to MLflow — not asserted, measured.
3. A rewrite moves the continuation prediction, and every point of the delta attributes to a named edit and the feature it moved.
4. Cohort × episode reactions computed as a single `ai_query`, blind to variant.
5. The regressor's held-out MAE is reported on unseen books; every prediction shows error bars.
6. Demo completes with zero ungoverned inference calls.
7. Local demo runs without credentials; Databricks mode fails loudly rather than silently degrading.
