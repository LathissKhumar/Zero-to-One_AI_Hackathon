# Session Handoff — CanonPulse

**Written:** 2026-07-26. **Branch:** `feat/extraction-eval` @ `13c6ca2`, 10 commits ahead of `main`.
**Suite:** 123 passing (`uv run --group dev pytest -q`). Working tree clean except two untracked files — see §7.

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

**Before adding any evaluation, ask: could this number fail? If not, it is not evidence.** Every prompt, fixture, and rule must be written without consulting `data/manifest/last_monsoon.yaml`.

---

## 4. The two numbers, and their honest descriptions

Use these sentences verbatim in any user-facing copy. Do not soften the zero.

| | Value | Honest description |
|---|---|---|
| **Ledger** | recall 1.0, precision 1.0, FPR 0.0 | *"Given a correct, hand-authored graph, the resolver separates all 6 real plot holes from all 5 intentional twists with no false positives. This measures graph traversal only, not extraction."* |
| **End-to-end** | recall 0.0, precision 0.0, FPR 1.0 | *"Run end-to-end through the offline heuristic extractor, the system recovers 0 of 6 real plot holes: it produces only 4 contradiction candidates across 220 episodes, locates 3 of the 11 contradiction-class items (all twists, none protected because their payoff links are missing or unverified), and misfires on all 3 clean controls."*|

**The zero is trustworthy, and that took two review rounds to establish.** The first version reported 0.167; a reviewer traced the single "recovered" hole to a numeric coincidence and showed the matcher *scrambled* — a byte-perfect extraction scored 0.833, and a +1 episode drift left 8/11 "matching" with 0 correct. After rebuilding matching around content agreement with order-free assignment, the extracted numbers came out **byte-identical across both a tightening and a loosening of the matcher**. That invariance is the evidence the number measures the extractor rather than itself.

**Why this is a better position than a single 1.0.** The pair localises where the difficulty lives: traversal is solved, text→graph is the hard part. A judge asking "what would make this fail?" can read the answer off the screen.

`app/evaluation.py` holds the matching rule. Its ceiling test (a byte-perfect extraction must score near-perfect) and scramble test (plausible-but-wrong content must not be credited) are what keep the scale valid — do not weaken either.

---

## 5. Immediate next work

### Task 4 — surface both numbers (not started, fully specified)

Brief already generated at `.git/sdd/task-4-brief.md`; plan section in the active plan file.

- `/api/discrimination` returns a flat `DiscriminationReport`. Change it to return `EndToEndReport` (`ledger`, `extracted`, `extraction_rejected`) from `app/evaluation.py::evaluate_series`. Compute once at startup via the existing `@lru_cache` pattern in `app/main.py`, not per request.
- Use `HeuristicExtractor()` for the served numbers. **Do not wire `LLMExtractor` into the app** — it needs credentials and would make the endpoint fail without a key.
- UI: never show the two numbers adjacent without labels saying what each measures. An unlabelled pair invites the reader to assume the higher one is the headline — that is the misleading single number this task exists to remove, with extra steps.
- README: its honesty section currently apologises for a metric that could not fall. Replace with the §4 framing. Keep every existing disclosure (synthetic series, synthetic training corpus, no real listener data). Record which manifest items the extractor recovers — anything aligning with `twist-02` or `twist-05` is an easy case by construction (see §3), so recovering those is weaker evidence than the other nine.
- Vanilla HTML/CSS/JS only. No frameworks, no CDN, no external fonts.

### Then: measure the LLM extractor

Built and tested offline in Task 3. Needs credentials:

```bash
export OPENAI_API_KEY=sk-...          # or DATABRICKS_ENDPOINT + DATABRICKS_TOKEN
uv run --group dev python scripts/measure_llm_extraction.py --limit 10   # cheap sanity check
uv run --group dev python scripts/measure_llm_extraction.py             # full run, 220 calls
```

Responses cache to `data/extraction_cache/` keyed by hash of (model, prompt), so re-measurement is free and a reviewer can verify without spending. Commit the cache. This converts the headline from a bare `0.0` into "heuristic floor 0.0, model extractor X" — the number that actually makes the product's claim.

---

## 6. Blocked on the human — and this is the biggest item on the board

**Databricks has never run.** No CLI installed, no `~/.databrickscfg`. The deployment assets are coherent and deployable (`sql/ddl.sql`, `databricks.yml`, `resources/`, `app.yaml`, and `tests/test_databricks_assets.py` pins that every SQL placeholder resolves), but nothing has ever executed against a workspace.

This is the sponsor track prize. The Databricks judge's question is "substrate or storage bill?" and there is currently no running answer.

```bash
curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
databricks auth login --host <workspace-url>
```

Then: `databricks bundle deploy`, run `sql/ddl.sql`, load the demo series into Delta, and run extraction and cohort batches through `ai_query`. The repo vendors the Databricks AI Dev Kit's own guidance at `.agents/skills/databricks-*` — read `databricks-apps-python`, `databricks-model-serving`, `databricks-bundles`, and `mlflow-onboarding` before deploying rather than guessing at bundle semantics.

**The credit position:** unlimited Databricks, ~$100 OpenAI (untouched, reserved for the Task 3 measurement and cold failover), $100 Codex.

---

## 7. Loose ends

**Untracked files that should probably be committed:** `AGENTS.md` and `PRODUCT.md` at repo root. Neither was created by the plan; both are useful. Review and commit.

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
