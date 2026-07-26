# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

**Immediate audience: hackathon judges** (Pocket FM, OpenAI, Databricks — 93 competing teams). They watch a short live demo, on a projector, with limited patience and a strong incentive to find the overclaim. The UI has to survive a skeptical follow-up question, not just look finished.

**Target audience the UI must credibly serve: writers and showrunners of serialized fiction.** They work on series running 200–500+ episodes, written by rotating teams on a release treadmill, often localized into 10+ languages. Their job at the moment of use is a pre-publish check: *before this episode ships, what did we already promise the reader, what is now contradicted, and what is overdue?* No human remembers what Episode 47 planted by the time Episode 312 is written.

The surface must read as a plausible tool for the second group while being demoed to the first. Judges first, but never at the cost of looking like a mockup.

## Product Purpose

CanonPulse is a standalone, platform-independent review system for serialized fiction. A writer submits a full series (up to ~300 episodes) and gets back:

- **Real plot holes**, separated from **intentional twists** the story pays off later.
- **Overdue obligations** — promises the story made and has not discharged, weighted by how long a reader tolerates the wait.
- **A predicted next-episode continuation**, with driving features, a named confidence interval, and an explicit disclosure that the model is fit to a synthetic corpus.
- **Rewrite attribution** — repair a real hole, see the predicted movement decomposed per edit, with the unattributed remainder reported rather than hidden.

Success is a writer (or judge) being able to argue with a specific verdict and land on the episode text that justifies it.

## Positioning

> Other tools help you write the next episode. CanonPulse protects the 300 you already shipped.

The mechanism a neighboring product cannot truthfully copy: a **dual-layer graph** where every narrative claim carries both the episode a reader encounters it in (`perceived_index`) and where it sits in story-time (`true_time`). A contradiction with a later payoff is protected as craft; a contradiction with nothing downstream is flagged as a defect. Resolution (`app/ledger.py`) is deterministic graph traversal, not a model call — the same series always yields the same verdict, and the verdict can be argued with.

Existing AI writing assistants are episode-local and captive to one platform. Nobody owns **series-lifetime obligation state**. Pocket FM is the reference register and beachhead customer, not the host environment.

## Operating Context

Two distinct scenes:

1. **Live demo, projector, unreliable Wi-Fi.** A 6-step sequence: load *The Last Monsoon* (220 episodes) → baseline flags vs CanonPulse breakdown → click a protected twist, show the Ep 47 → Ep 218 payoff citation → predicted continuation panel with interval and disclosure → "Simulate repair" on a real hole, show per-edit attributed delta and unattributed remainder → MLflow run with discrimination precision/recall and held-out MAE.
2. **Writer's pre-publish check.** Repeat task work against a live ledger, mid-series, with a deadline.

The Databricks-hosted path is deployed and verified side by side with local mode: batched `ai_query` extraction over Delta, the cohort divergence query, MLflow-tracked training, and a Databricks App deployment. Every identifier there is a supplied parameter — catalog, schema, SQL warehouse, model-serving endpoint, MLflow experiment. No credential lives in the repository.

## Capabilities and Constraints

Shipped and served:

- `GET /api/series`, `GET /api/audit`, `GET /api/discrimination`, `GET /api/predict?episode=N`, `POST /api/rewrite`.
- Both rewrite predictions are computed server-side from the same trained predictor, so `total_delta` is never a caller-supplied value.
- Offline fallback: `/api/predict` runs inference in a worker thread under `INFERENCE_TIMEOUT_SECONDS` (5s); on timeout the response flips to `golden_path()` (`app/demo_mode.py`) and marks itself `"degraded": true`. The fallback recomputes through the real `LedgerResolver` — nothing hardcoded or fabricated.
- Frontend is static HTML/CSS/JS (`app/static/`) served by FastAPI, no build step. The local demo needs no credentials and no network.

Built but deliberately **not served**: `app/cohorts.py` (five fixed, transparent weight vectors over structural features). Tested, reachable only from tests, not on the demo path, until a decision is made to serve it.

Planned surfaces, **not shipped** — record as roadmap, never as existing: Series Memory, Pre-Publish Check, Writer Handoff Sheet, Showrunner Debt Board, Localization Continuity Check. Also planned and not on the demo path: two-speed ingest (fast synopsis pass yields a usable ledger in minutes; deep extraction backfills per episode).

CanonPulse continues past the hackathon; the hackathon build is v0.

## Brand Commitments

Name: **CanonPulse**.

**Vocabulary is serialized-fiction native and platform-agnostic.** Episodes, not chapters. Series, not novel. Listeners and readers, not "audience." Showrunner and writer, not author. The metric surfaces as **next-episode continuation**; "continue-to-read" is the training label and never the product language. Pocket FM is a reference register, not a host — no platform lock-in language.

Voice: plainly stated, argues with itself in public, refuses to round a caveat off. The honesty sections in the README are the register, not an appendix to it.

## Evidence on Hand

Real and committed:

- `data/series/last_monsoon.json` — *The Last Monsoon*, 220 episodes, original and synthetic, generated for this project. Not a real published work; no claims are made about any real series.
- `data/manifest/last_monsoon.yaml` — hand-authored manifest.
- `app/training_corpus.py` — deterministic offline synthetic corpus with a fully stated generative formula.
- MLflow runs: `held_out_mae`, split strategy, feature order, fitted model, and discrimination metrics with explicit ledger/extracted prefixes.
- Every finding carries an episode excerpt behind it.

Absences future work must **not** fabricate:

- **No real reader-retention corpus exists in this repository.** No real listener or reader data is used, claimed, or available anywhere in this system. The real corpora (arXiv 2412.15239, Qidian, Royal Road) are out of scope.
- The predicted continuation is **not calibrated to any real audience**. Never present it as a measured retention rate.
- `/api/discrimination` reports two explicitly separated blocks: the authored-graph ledger number measures traversal only, while the end-to-end block runs the offline heuristic extractor over raw episode text. The ledger number is not extraction evidence; the end-to-end number is the honest extractor floor. `app/manifest.py` enforces this: no test may assert a discrimination metric equals `1.0`.
- No testimonials, customers, benchmarks, pricing, or licensing claims exist. Do not invent them. The deployed Databricks App is an implementation artifact, not a customer or production-scale claim.

## Product Principles

1. **Nothing surfaces without its citation.** No number, verdict, or claim appears on screen unless the episode text justifying it is reachable in one click. This is the product, not a nicety.
2. **The caveat stays as loud as the number.** Synthetic-corpus disclosure, the no-real-reader-data statement, and the discrimination caveat are permanent UI content. Never soften, shrink, or bury them for visual polish; a prediction shown without its disclosure is a defect.
3. **Determinism is the argument.** The verdict comes from graph traversal, not a model call, so it is reproducible and contestable. Design should make the reasoning inspectable rather than oracular.
4. **Report the remainder.** Unattributed prediction movement, clamped values, and degraded fallbacks are shown, not hidden. Whatever the system cannot explain, it says so.
5. **Platform-agnostic by construction.** The ledger is a graph and therefore language- and platform-independent. Vocabulary, framing, and surfaces stay standalone.

## Accessibility & Inclusion

Projector legibility is a real constraint of the primary demo scene: contrast and type size must survive a washed-out projected image at distance. No product-specific standard has been established beyond that.
