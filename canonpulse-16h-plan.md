# CanonPulse — 16-Hour Build Plan
### Standalone series-continuity and retention studio for serialized-fiction writers

**Team:** 3 people (48 person-hours). **Window:** 16h wall-clock. **Frozen at h14.**

Judges: Pocket FM · OpenAI · Databricks. 93 teams.

---

## Positioning

**Standalone product. Platform-independent.** Not a module inside anyone's studio. The user is the writer or writing team producing serialized episodic fiction — for Pocket FM, Kuku FM, Audible Originals, Wattpad, Royal Road, Seekho, indie audio-drama, or their own channel. Pocket FM is the **reference register and beachhead customer**, not the host environment.

> **Other tools help you write the next episode. CanonPulse protects the 300 you already shipped.**

The category gap: serialized fiction runs 200–500+ episodes, written by rotating teams, on a release treadmill, often localized into 10+ languages. No human remembers what episode 47 planted by the time they write episode 312. Existing AI writing assistants operate on the episode in front of you. Nobody owns **series-lifetime obligation state** — what was planted, what is owed, what is overdue.

Where the platforms do ship assistants (Pocket FM's CoPilot does logic checks, cliffhanger suggestions, character bios, localization), they are episode-local and captive to one platform. The long tail of serialized writers — the majority — has no tooling at all.

Five surfaces, all falling out of one ledger:

| Surface | What it does |
|---|---|
| **Series Memory** | Ledger persists across the series lifetime. Answers "what did we plant in Ep 47?" at Ep 312. |
| **Pre-Publish Check** | Run before shipping an episode. Twist-vs-hole discrimination, overdue obligations, predicted continuation. |
| **Writer Handoff Sheet** | Multi-writer series: "you inherited 7 open obligations from Writer A, 3 overdue." Shared team state. |
| **Showrunner Debt Board** | Obligation debt across every running series. Portfolio risk for a team producing many at once. |
| **Localization Continuity Check** | The ledger is a graph, therefore language-independent. Validates translated episodes against the same obligations. |

**Onboarding — the standalone-product risk.** A cold user arrives with 200 already-published episodes; full extraction over all of them is slow and metered. Answer: **two-speed ingest.** A fast synopsis-level pass yields a usable ledger in minutes; deep extraction backfills in the background per episode. The ledger is useful before ingest finishes. Not on the demo path (corpus is pre-ingested) but have the answer ready — a judge will ask.

**Vocabulary is serialized-fiction native, platform-agnostic.** Episodes not chapters. Series not novel. Listeners and readers, not "audience." Showrunner and writer, not author. The metric surfaces as **next-episode continuation** — "continue-to-read" is the training label, never the product language.

---

## 0. Architecture in one page

```
SERIES INGEST — writer's full submission script, up to 300 episodes (~500k words)
        │   two-speed: fast synopsis pass → usable ledger in minutes
        │              deep extraction backfills per episode in background
        │   ** batch ai_query over Delta rows — a Spark job, not a for-loop **
        │
        ▼
  EXTRACTION  ──►  DUAL-LAYER GRAPH  ──►  G_true (chronological reality)
                                     └──►  G_perceived (audience information order)
        │
        ▼
  LEDGER TRAVERSAL — every discrepancy resolves to one of three states:
        SUSPENDED    payoff exists downstream        → PROTECT (intentional twist)
        BROKEN       contradiction, no payoff        → SURGICAL NODE REPAIR
        OUTSTANDING  payoff unwritten, story ongoing → WARN (narrative debt, urgency-ranked)
        │
        ├──► WRITERS ROOM (5 LLM personas → structured graph annotations, not prose)
        ├──► NON-LINEAR SCRAMBLER (edits G_perceived, leaves G_true invariant)
        └──► FEATURE VECTOR
                   │
                   ▼
        TRAINED REGRESSOR (labels: public serial-fiction continue-to-read)
                   │        ** sees graph features ONLY, never prose **
                   ▼
        CONTINUE-TO-READ % ± CI  per chapter boundary
                   │
                   ▼
        REWRITE → recompute features → SAME FROZEN MODEL → Δ with per-edit attribution
```

**The load-bearing property:** the predictor consumes graph features, never text. A prettier sentence cannot move the score. Only structural change — closing an obligation, shortening payoff distance, raising urgency — moves it. The rewriter is physically incapable of flattering itself. State this explicitly on stage; it is the strongest methodological claim in the build.

---

## 0.5 Three data streams — keep them straight

| Stream | What it is | Where it comes from | Shown to user? |
|---|---|---|---|
| **Product input** | The writer's series submission, up to 300 episodes as text | The user | Yes — it's their work |
| **Demo asset** | One 220-episode series shown on stage | Authored by your team (§1.5) | Yes |
| **Training data** | Labeled retention corpora fitting the regressor | arXiv / Qidian / Royal Road | **Never** — model weights only |

Only the training stream needs public data. Confusing these three is what produces an incoherent pitch.

**Why scale is the moat.** A 300-episode submission is roughly half a million words, on the order of a million tokens. This pre-empts the obvious objection:

> *"Why not paste it into a long-context model?"* — Cost per revision is prohibitive, attention degrades badly across that span, and the product needs persistent structured state you can query, diff, and traverse, not a summary regenerated on every run.

It is also why Databricks is load-bearing rather than decorative: **300-episode extraction is one `ai_query` over 300 Delta rows, parallel across the cluster.** Say that sentence on stage. No other team will demo series-scale analysis at this volume.

---

## 1. Corpus fusion — three sources, one target (TRAINING ONLY)

Fits the regressor. Never surfaced in the product.

Do **not** pool raw. Label semantics differ.

| Source | Native label | Role |
|---|---|---|
| arXiv 2412.15239 corpus (30,258 chapters / 1,735 books) | **continue-to-read rate** — direct | Primary. Closest analog to Pocket FM's coin-unlock decision. |
| Qidian-Webnovel Corpus (openly licensed, chapter + paragraph reader response) | reader response counts | Secondary. Cross-lingual robustness; serialized-genre match. |
| Royal Road (per-chapter view counts, scraped) | views(ch_n)/views(ch_n−1) | Tertiary. Noisy but English and genre-adjacent. Only if time permits. |

**Normalization:** z-score the retention target *within each book*. Cross-platform absolute scales are meaningless; within-story deltas are what transfer. Include `platform` as a categorical feature so the model can absorb residual offset.

**Split by `book_id`, never by chapter.** Chapters from one book straddling train/test is leakage and it will inflate your metric. Report held-out MAE on unseen books. Say "grouped split by book" out loud in the pitch — it signals you know what you're doing.

**Fallback if scraping/download stalls past h3:** train on the arXiv corpus alone. One clean source with real labels beats three half-ingested ones. This is a pre-declared cut, not a judgment call in the moment.

---

## 1.5 Demo asset — *The Last Monsoon*, 220 episodes

Original Pocket-FM-register series. Mumbai thriller. Generated, but human-anchored.

**The manifest is written by hand, before any generation.** If a model both authors the series and plants the defects, the ground truth is worthless — the analyzer would be graded against another model's intent. So: the team writes a defect manifest first, generation is *conditioned* on it, and the manifest is held out from the system under test. Use a different prompt path for generation than for analysis. The analyzer never sees the manifest.

**Defect budget — 20 labeled items:**

| Class | Count | Purpose |
|---|---|---|
| Accidental holes — contradiction, no payoff anywhere | 6 | Recall on real defects |
| Intentional twists — contradiction-shaped, payoff exists downstream | 5 | The differentiator. Include one unreliable narrator, one flashback misreadable as present-tense, one identity reveal |
| Outstanding obligations — planted, unpaid | 6 | 3 overdue, 3 healthy. Tests urgency ranking |
| Clean control boundaries | 3 | False-positive rate |

**Structure:** beat-level synopses for all 220 episodes; full text for 10 at the pressure points (Ep 1, 12, 47, 88, 134, 178, 199, 210, 218, 220). The ledger spans all 220. Ep 218 paying off a plant from Ep 47 is a **171-episode span** — the long-range claim lands with real distance behind it.

**Generation is two-stage.** First the arc skeleton — acts, turning points, character threads, the manifest's plant/payoff positions. Then batch-generate beats conditioned on skeleton + manifest. One-shot generation of 220 beats produces incoherent mush.

Say on stage that the demo series is original and synthetic. It's a tool demo; nobody expects a real client's IP.

---

## 2. Feature vector (graph → model)

Deterministic, computed by traversal. No LLM in this path.

```
open_obligation_count        obligations open at this boundary
mean_urgency                 urgency-weighted mean of open obligations
min_payoff_distance          chapters until nearest scheduled payoff
mean_payoff_distance
planting_recency             chapters since most recent clue plant
suspended_edge_density       protected twists per chapter (proxy for structural ambition)
broken_edge_count            unrepaired contradictions
fair_clue_density            clues planted before their reveal / total reveals
sentiment_velocity           Δ valence across the boundary
perceived_time_jump          |G_perceived index − G_true index| at boundary
character_thread_count       active character threads
platform                     categorical (training only)
```

`perceived_time_jump` is the feature that only exists because you built two graphs. Point at it in the pitch.

---

## 3. Team split

| Lane | Owner | Scope |
|---|---|---|
| **A — Data & Model** | Dev 1 | Corpora ingest, normalization, feature table, regressor training, MLflow runs, held-out MAE, seeded-defect precision/recall |
| **B — Graph & Agents** | Dev 2 | Extraction, dual-layer graph, backward causal payoff test, ledger states, surgical node repair, non-linear scrambler, 5 Writers Room personas, cohort `ai_query` |
| **C — Platform & UI** | Dev 3 | Databricks CLI + auth, Unity Catalog schema, Delta tables, Vector Search index, Databricks App deploy, the entire frontend |

Lane C is the critical path. UI is where hackathon builds die. Dev 3 does **nothing else**.

---

## 4. Hour-by-hour

### h0 – h1 · Unblock everything
- **All three, first 30 min:** write the defect manifest by hand (§1.5). Twenty labeled items, positions fixed. This is your ground truth and the headline number depends on it. Do it together, once, then it's frozen.
- **C:** install `databricks` CLI, authenticate, confirm workspace write access, create catalog + schema. **This blocks A and B — start it before the manifest session and let it run.** Verify Foundation Model APIs are callable and record which models are currently serving, with retirement dates.
- **A:** start arXiv corpus download in background. Begin Qidian.
- **B:** arc skeleton for *The Last Monsoon* — acts, turning points, character threads, manifest plant/payoff positions.

**Checkpoint h1:** workspace live, manifest frozen, corpus downloading, skeleton done. If CLI auth is not finished at h1, all three stop and fix it.

### h1 – h3 · Foundations in parallel
- **A:** normalize corpora, grouped split by book, land training table in Delta.
- **B:** batch-generate 220 beats conditioned on skeleton + manifest, plus 10 full episodes. Land in Delta. Then extraction pass — entities, events, claims, clues, obligations, emotional beats → JSON, as one `ai_query` over episode rows. Build `G_true` and `G_perceived` in NetworkX.
- **C:** Delta DDL for all tables, Vector Search index on episode excerpts, skeleton Databricks App deployed and reachable at a URL.

**Checkpoint h3:** a URL exists that returns a page. A 220-episode graph exists. A training table exists.

### h3 – h6 · Core engine
- **A:** feature extraction over training corpus, train regressor, log to MLflow, report held-out MAE. **First real number.**
- **B:** backward causal payoff test. Ledger state resolution (suspended / broken / outstanding). Retrieval-cited evidence for every state assignment.
- **C:** Story Health panel + evidence drawer wired to real Delta reads.

**CUT GATE h6** — if the ledger does not classify the manifest's items correctly: drop the scrambler and micro-foreshadowing entirely, reallocate Dev 2 to hardening classification. Twist-vs-hole discrimination *is* the demo; nothing else matters if it doesn't work.

### h6 – h10 · The differentiators
- **A:** run discrimination eval against the manifest → **precision/recall on holes-caught vs twists-protected**, plus false-positive rate on the 3 clean controls. Log to MLflow. Build the baseline comparison (naive consistency checker that flags every contradiction) — this is the side-by-side.
- **B:** Surgical Node Repair (rewrite only the corrupted node, diff-preserving). Non-linear scrambler on `G_perceived`. Writers Room personas → structured graph annotations.
- **C:** the side-by-side comparison view. Baseline column vs CanonPulse column. **This is the mic drop screen — it gets the most polish of anything in the build.**

**CUT GATE h10** — if the side-by-side isn't rendering: cut Writers Room to 3 personas, cut micro-foreshadowing, cut cohort heatmap. Ship dual-graph + repair + prediction only.

### h10 – h13 · Linkage and payoff
- **A:** counterfactual scoring — rewritten graph through the frozen model, Δ with CI, per-edit attribution table.
- **B:** cohort pass as a single `ai_query` over (cohort × chapter) — 5 × 40 rows, one SQL statement. Blind: strip version labels, randomize order.
- **C:** attributed diff view (hunk | obligation discharged | Δ continue-to-read), cohort heatmap, discovery screen (mood search + explain-why off the obligation index).

**CUT GATE h13** — cut the discovery screen first, then the cohort heatmap. Never cut the attributed diff.

### h13 – h14 · Harden
- Pre-warm every serving endpoint. Precompute the entire golden path and cache it. Offline bundle that renders the full demo from cached Delta reads with zero live inference. Trigger condition for switching to it: any call >5s.
- Verify the $100 OpenAI failover path works but is unused. Target: **zero ungoverned inference calls during the demo.**

### h14 – h16 · Frozen. Rehearsal only.
No new code. Run the demo end to end at least six times. Time it. One person drives, one watches the clock, one watches for errors.

---

## 5. Demo choreography

**0–30s — the mic drop.** Load *The Last Monsoon* — 220 episodes, ~500k words. One click. Split screen:

> **Baseline consistency checker: 17 issues flagged**
> **CanonPulse: 6 real holes · 5 twists protected · 3 obligations overdue · 3 clean**

Click any protected twist → evidence drawer → *"Protected: Ep 218 pays this off. Planted Ep 47. Cited."* — a 171-episode span, on screen.

No narration needed. The judge understands instantly. **This is why you win: every consistency checker on the market over-flags intentional non-linearity. You don't — and you do it across 220 episodes, not one.**

**30–75s — repair and predict.** Surgical repair on one real hole. Diff shown, 99% of prose untouched. Boundary prediction moves 61% → 78% ± 4. Attribution table shows which edit moved which feature by how much.

**75–105s — the audience.** Cohort × chapter heatmap. Mystery Purist drops at ch.12 where nobody else does. One `ai_query`. Say the sentence: *"the entire audience simulation is one SQL statement over a governed Delta table."*

**105–120s — the loop closes.** Flip to discovery. The same obligation ledger answers *"something that feels like a rainy Sunday after heartbreak"* — and "Explain Why" cites the literal unresolved-longing dimensions. Creation side and discovery side, one primitive.

---

## 6. Per-judge beats

| Judge | Their question | Your beat | Timestamp |
|---|---|---|---|
| **Pocket FM** | "Would our writers use this? Would we buy it?" | Next-episode continuation is the coin-unlock atom. Overdue-obligation warning at Ep 199. Reviewer-side triage: 300-episode submissions ranked in minutes instead of skimmed and gambled on. | 30–75s |
| **OpenAI** | "Is the multi-agent design load-bearing or theater?" | Predictor is blind to prose. Blind cohort eval. Grouped-by-book split. Seeded-defect precision/recall in MLflow. | 0–30s + 75–105s |
| **Databricks** | "Substrate or storage bill?" | Whole audience simulation as one `ai_query`. Unity Catalog lineage from warning back to source chapter. All inference on Foundation Model APIs — zero external calls. | 75–105s |

---

## 7. Honesty rules — non-negotiable

- Say the training corpus is public serialized fiction, not Pocket FM data. Say the method transfers unchanged.
- Report the model's held-out MAE. Show error bars on every prediction.
- Never state a number you cannot decompose on request.
- Do not quote Pocket FM's internal metrics. A judge from the company is in the room.

---

## 8. Immediate first 30 minutes

1. Dev 3: install the `databricks` CLI, authenticate, create catalog + schema, confirm write access. **Everything blocks on this — start it first and let it run.**
2. Dev 1: start the arXiv corpus download in the background.
3. **All three together, 30 minutes: write the defect manifest by hand.** Twenty labeled items — 6 accidental holes, 5 intentional twists, 6 outstanding obligations, 3 clean controls — each pinned to an episode number, with plant and payoff positions. Then freeze it. This is your ground truth; the headline precision/recall number and the entire mic-drop screen depend on it being authored by humans rather than by the model under test.
4. Dev 2: arc skeleton for *The Last Monsoon*, conditioned on the frozen manifest.
