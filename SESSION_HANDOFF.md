# Session Handoff — CanonPulse

**Written:** 2026-07-26, updated after the final whole-branch review.
**Branch:** `feat/extraction-eval` @ `a6ea65b`, 16 commits ahead of `main`.
**Suite:** 124 passing (`uv run --group dev pytest -q`). Working tree clean except two untracked files — see §7.
**Plan status:** all 4 tasks of `2026-07-26-canonpulse-extraction-eval.md` complete; final review's blocking findings fixed.

You are picking up a hackathon build mid-flight. Read §1 and §3 before touching anything.

---

## 1. How to resume

**Use superpowers.** In Codex, skills load natively — follow the instructions a skill presents when it activates. The workflow in use is:

```
brainstorming → writing-plans → subagent-driven-development
```

with `test-driven-development` inside every task. Do not skip to implementation; three separate defects in this repo were caused by skipping a gate, and each is documented below.

**Check the progress ledger first — it is the recovery map:**

```bash
cat "$(git rev-parse --git-path sdd)/progress.md"
```

Tasks marked complete there are done. Do not re-dispatch them. The ledger names commits that exist in git even when conversation memory does not. Trust it and `git log` over recollection.

**`AGENTS.md`** (repo root) carries build/test/style conventions. Codex reads it natively.

**Active plan:** `docs/superpowers/plans/2026-07-26-canonpulse-extraction-eval.md` — Tasks 1–3 complete, **Task 4 not started**.

---

## 2. What this product is

CanonPulse is a standalone, platform-independent review system for serialized fiction. A writer submits a full series (up to ~300 episodes, ~500k words). It returns real plot holes separated from *intentional* narrative twists, overdue narrative obligations, and a predicted next-episode continuation — all with cited evidence.

The central claim: **every consistency checker on the market flags intentional non-linearity as an error, which is why writers ignore them. This one doesn't.** A contradiction the story later acknowledges is protected craft; the same contradiction with nothing downstream is a defect. That discrimination is the demo.

`PRODUCT.md` holds the fuller product framing and the audience analysis. `docs/superpowers/specs/2026-07-25-canonpulse-dual-layer-graph-design.md` is the architecture spec.

---

## 3. Invariants — breaking any of these silently invalidates a number shown to judges

These were each established by a review that caught a live violation. They are not style preferences.

1. **The predictor never sees prose.** `BoundaryFeatures` / `FEATURE_ORDER` are structural only. This is what stops a rewrite from raising its own score by sounding better. Adding any text-derived feature destroys it.
2. **No feature reads past its boundary.** A feature at episode *b* consulting episode *b+1* inflates offline metrics and collapses in production. `tests/test_features.py::test_features_ignore_everything_after_the_boundary` is the guard — it must mutate entries *and* nodes, not just payoffs. (It originally only mutated payoffs and therefore missed a real lookahead bug.)
3. **An unverified payoff link never protects a contradiction.** `PayoffLink.verified` gates protection in `app/ledger.py::_find_payoff`. Extracted links are `verified=False`, so extraction-derived twists resolve `broken` by design. The demo series' authored links carry `verified: true` in the data — trust is explicit in the fixture, never by weakening the check.
4. **No test may assert a quality metric equals `1.0`.** Bound results (`> 0.9`). The superseded plan specified `assert precision == 1.0`, so the implementation was written to satisfy it and measured nothing.
5. **Never fabricate data to make a number exist.** Task 3 correctly refused to write a fake LLM response cache without credentials. A fabricated input produces a fabricated metric.
6. **100% of product runtime inference runs on Databricks Foundation Model APIs.** A direct vendor call generates no Unity Catalog lineage and no MLflow trace, and erodes the sponsor track prize. `LLMExtractor`'s OpenAI path exists *only* for offline measurement and must never be presented as the governed path — that is why `ExtractionResult.backend` exists.
7. **Generators stay deterministic and offline.** Regenerating must be byte-identical.

### The circularity trap — it came back three times

This is the single most important thing to understand about this repo.

- **First:** `run_benchmark` "detected" a case exactly when the case was labelled detectable. Deleted.
- **Second:** the demo series is *generated from* the manifest it is scored against, so the resolver trivially recovered it. This is why the two-number split in §4 exists.
- **Third:** the plan's own test fixture paraphrased two manifest defects, silently tuning the extractor to them. Caught in review; fixture rewritten, `swim`/`dive` synonym cluster removed.
- **Fourth:** `_episode_rows` fed the extractor `node.summary` — generator output conditioned on the manifest, which often states a defect outright. Seven of the nine promise-class anchors had their promise language *only* there and none in the episode prose, so `false_positive_rate` and `obligations_tracked` were manufactured (1.0 and 6/6 with summaries; 0.0 and 2/6 without). Contradiction detections were byte-identical either way, so the headline never depended on it — but two numbers reported beside it did, and all three were on screen and in this document. Fixed in `735f903`; `_episode_rows` now uses excerpt prose only.
- **Fifth (methodology, same family):** the ceiling test read each entry's expected state out of the manifest and never ran `LedgerResolver`, so it validated the matcher while claiming to validate the end-to-end scale. Fixed in `a6ea65b` — it now feeds a byte-perfect extraction through `evaluate_series` and scores 1.0/1.0/0.0 via the real path.

**Before adding any evaluation, ask: could this number fail? If not, it is not evidence.** Every prompt, fixture, and rule must be written without consulting `data/manifest/last_monsoon.yaml`.

---

## 4. The two numbers, and their honest descriptions

Use these sentences verbatim in any user-facing copy. Do not soften the zero.

| | Value | Honest description |
|---|---|---|
| **Ledger** | recall 1.0, precision 1.0, FPR 0.0 | *"Given a correct, hand-authored graph, the resolver separates all 6 real plot holes from all 5 intentional twists with no false positives. This measures graph traversal only, not extraction."* |
| **End-to-end** | recall 0.0, precision 0.0, FPR 0.0 | *"Run end-to-end through the offline heuristic extractor, the system recovers 0 of 6 real plot holes and protects 0 of 5 intentional twists. It produces 4 contradiction candidates across 220 episodes; 3 are matched to a manifest item, but only one (`twist-02`) has both endpoints right — and `twist-02` is an easy case by construction. The 3 clean controls are not over-flagged: they resolve `outstanding`, meaning the extractor found the promise and missed the payoff."* |

**Two things to say out loud rather than let a judge find them:**

1. **The reachable precision ceiling is 0.55, not 1.0.** Protection requires a *verified* payoff link by design, and no extractor in this repo can emit one — no `Verifier` implementation exists, and `app/main.py` uses a bare `LedgerResolver()`. So `twists_protected` measures the absence of a verifier rather than the extractor, and every twist correctly located strictly *lowers* extracted precision (a located-but-unprotected twist counts as `twists_flagged`). Read `precision 0.00` against 0.55.
2. **The big `11 → 6 / 5 / 3` panel is the traversal number.** It now carries a provenance label saying so. Do not remove it.

**The zero is trustworthy, and that took two review rounds to establish.** The first version reported 0.167; a reviewer traced the single "recovered" hole to a numeric coincidence and showed the matcher *scrambled* — a byte-perfect extraction scored 0.833, and a +1 episode drift left 8/11 "matching" with 0 correct. After rebuilding matching around content agreement with order-free assignment, the extracted numbers came out **byte-identical across both a tightening and a loosening of the matcher**. That invariance is the evidence the number measures the extractor rather than itself.

**Why this is a better position than a single 1.0.** The pair localises where the difficulty lives: traversal is solved, text→graph is the hard part. A judge asking "what would make this fail?" can read the answer off the screen.

`app/evaluation.py` holds the matching rule. Its ceiling test (a byte-perfect extraction must score near-perfect) and scramble test (plausible-but-wrong content must not be credited) are what keep the scale valid — do not weaken either.

---

## 5. Immediate next work

**Task 4 is done.** `/api/discrimination` returns `EndToEndReport`, both numbers render with labels that are static HTML (so no loading or fetch-failure state can show a bare figure), and the README carries the two-number framing. The final whole-branch review's blocking findings are fixed.

**Remaining findings from that review, deliberately deferred — triage before merge:**

| Finding | Where | Verdict |
|---|---|---|
| Mutual-best charges the better of two correct detections as a false positive. `contradiction-3-60` is the genuinely correct twist-02 detection (both endpoints right) but loses to `contradiction-60-134`, stays unmatched, and lands in `spurious_broken`. | `app/evaluation.py:99-107`, `app/manifest.py:111` | Invisible today (precision is 0.0 regardless). Live the moment `holes_caught > 0`. |
| The content gate is tautological for the matches it credits: `_entry_content_words` draws from the entry's own cited excerpts and `_manifest_item_content_words` from the anchor episode's excerpt, so when an entry cites the excerpt *at* an anchor both sets come from the same text and overlap ≈1.0 by construction. It is a real filter only for entries that bracket an anchor without citing it. | `app/evaluation.py:295,326` | Ship, but do not describe the gate as verifying semantic agreement. |
| `LedgerEntry.entities` is set to the episode's whole content-word bag, and `app/features.py:107` counts entities into `active_thread_count`. The extracted graph never reaches the feature path today (`app/main.py` uses the authored series), so "the predictor never sees prose" holds — but nothing guards the seam. | `app/heuristic_extractor.py:245,258,287` | Hard blocker before wiring the extracted graph into `/api/predict`. |
| No test asserts the extractor ever produces a `contradiction` entry, despite the fixture being built to exercise exactly that. | `tests/test_heuristic_extractor.py` | Ship; cheap to add. |
| `DiscriminationReport.baseline_flags` is `len(holes)+len(twists)` and never touches `resolved`, so the `extracted` block serves `baseline_flags: 11` copied from the answer key. | `app/manifest.py:131` | Ship, but do not present it as an extracted result. |

### Next: measure the LLM extractor

Built and tested offline in Task 3. Needs credentials:

```bash
export OPENAI_API_KEY=sk-...          # or DATABRICKS_ENDPOINT + DATABRICKS_TOKEN
uv run --group dev python scripts/measure_llm_extraction.py --limit 10   # cheap sanity check
uv run --group dev python scripts/measure_llm_extraction.py             # full run, 220 calls
```

Responses cache to `data/extraction_cache/` keyed by hash of (model, prompt), so re-measurement is free and a reviewer can verify without spending. Commit the cache. This converts the headline from a bare `0.0` into "heuristic floor 0.0, model extractor X" — the number that actually makes the product's claim.

---

## 6. Databricks — live, and what actually works

**Workspace is authenticated and the pipeline runs.** CLI v1.9.0, profile `DEFAULT`,
host `dbc-53cf8438-33aa.cloud.databricks.com`. Warehouse `c4cfcc95726ac7d5`
(Serverless Starter, 2X-Small — **stops itself**, restart before demoing).

| Piece | State |
|---|---|
| Schema `writers_room.canonpulse` | ✅ all 14 tables, matching `sql/ddl.sql` exactly |
| Demo data in Delta | ✅ loaded — 220 episodes / 220 excerpts / 220 nodes / 20 entries / 8 payoffs / 20 manifest items / 5 cohorts, via `scripts/load_databricks.py` (idempotent) |
| `ai_query` | ✅ works |
| Structured output | ✅ works via **`json_schema`** responseFormat |
| `sql/cohort_reactions.sql` | ✅ verified end to end — 20 structured verdicts, 5 cohorts × 4 episodes, cohorts genuinely disagreeing |
| `sql/extract_graph.sql` | ✅ verified — `parse_extraction_row` accepts the output (ep 3: 1 node/1 entry; ep 47: 4 nodes/1 entry). Before the fix every row would have been rejected. Slow: nested strict schema takes minutes over 220 episodes. |
| `databricks bundle validate` | ✅ OK |
| `databricks bundle deploy` | ❌ never run |
| App reading from Databricks | ❌ **`app/main.py` has no Databricks reference at all** — it reads committed JSON |

**Three defects that only live deployment could find** (fixed in `28c852c`), all in files
`tests/test_databricks_assets.py` asserts are parameterized but never executes:

1. Both SQL statements used the DDL-string `responseFormat`. That form permits exactly
   **one top-level field**; a 4-field struct fails with
   `AI_FUNCTION_UNSUPPORTED_RESPONSE_FORMAT.DDL_STRING`. Use the `json_schema` form.
2. `extract_graph.sql` had **no `responseFormat` at all**, so the model wrapped output in
   ```` ```json ```` fences. `parse_extraction_row` rejects those — extraction would have
   returned an empty graph with `rejected == row count` while reporting success.
3. `databricks-gpt-5-6-luna` is **not supported for batch inference**. The bundle's
   `databricks-gpt-oss-20b` default is correct and works.

**The honest gap:** data, SQL and inference are verified on-platform, but the *application*
does not consume any of it. Wiring `app/main.py` to read from Unity Catalog — or deploying
the bundle so the app runs on Databricks Apps — is the remaining work for the track prize.
The repo vendors the AI Dev Kit's guidance at `.agents/skills/databricks-*`; read
`databricks-apps-python`, `databricks-bundles` and `mlflow-onboarding` before deploying.
Note the CLI suggests `databricks aitools install` for those skills.

**MLflow has never run** — no experiment, no logged training run, no traces, despite the
spec naming MLflow as one of four load-bearing primitives.

**Credit position:** unlimited Databricks, ~$100 OpenAI (untouched — reserved for the
`scripts/measure_llm_extraction.py` run and cold failover), $100 Codex.

---

## 7. Loose ends

**Untracked files at repo root:** `AGENTS.md` and `PRODUCT.md`. Neither was created by the plan.

- `AGENTS.md` — build/test/style conventions, Codex reads it natively. Safe to commit.
- `PRODUCT.md` — **do not commit as-is.** Two sections are now false: it still describes the superseded single-1.0 metric framing this branch replaced, and it lists MLflow runs under "Real and committed" though Databricks has never executed. Fix both first.

**Deferred Minor findings** (full list with rationale in the ledger):

- `LedgerEntry.excerpt_ids` is model-trusted in both `LLMExtractor` and `DatabricksExtractor`, unlike `PayoffLink.verified` which is force-overridden. `PRODUCT.md` promises every finding carries an excerpt. `app/evaluation.py` has an entity fallback, so not a regression — but worth a guard.
- `app/static/app.js` builds DOM via `innerHTML` from server strings. Harmless on synthetic fixtures; a real XSS vector the moment the product ingests actual writer scripts, which is its stated purpose.
- The two-speed ingest described in the spec (fast synopsis pass, deep backfill) is not implemented. A cold user with 300 episodes has no working upload path.
- `data/series/last_monsoon.json` node summaries sometimes state a defect outright (*"Despite swearing weeks ago that she cannot swim, Tara dives…"*), because they are generator output conditioned on the manifest. This makes "derived from episode text" weaker than it sounds and is an optimistic bias on the end-to-end number. Documented in `app/evaluation.py`; do not quietly rely on it.
- Cohorts (`app/cohorts.py`) are built and tested but deliberately unwired from the served product. The cohort SQL prompts on prose profiles rather than the structural weight vectors that make cohorts differ — fix that if wiring them in.

**Not implemented from the spec's architecture diagram:** the non-linear scrambler, micro-foreshadowing injection, and the five Writers Room craft personas. These were pre-declared cut-gate items, not oversights.

---

## 8. Honesty rules for the demo

The product's whole pitch is that its numbers are checkable. Two standing disclosures must survive any edit:

- The demo series is **original and synthetic**. The continuation model is fit to a **synthetic corpus with a documented generative process** (`app/training_corpus.py`), not to observed reader behaviour.
- No real platform telemetry or listener data is used or claimed anywhere.

A false claim on screen is a product defect here, not a copy nit. One already shipped and had to be fixed: the README was corrected when the synthetic corpus landed, but the dashboard footer kept asserting the model was "trained on public serialized fiction" for three more commits. **When a claim changes, grep the served UI, not just the docs.**
