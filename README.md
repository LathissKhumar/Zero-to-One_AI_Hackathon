# CanonPulse

Implementation scope is tracked in [`canonpulse-16h-plan.md`](canonpulse-16h-plan.md); the eight execution plans are under [`docs/superpowers/plans/`](docs/superpowers/plans/).

Validate locally with:

```bash
uv run --group dev pytest
```

The demo series, cohort reactions, and continuation predictions are synthetic and are not observed reader behavior.

> Every clue, vow, wound, threat, and romance arc is a promise made to a reader. CanonPulse tells a writer which of those promises are broken, which are intentional twists still waiting on their payoff, and which are overdue — with the exact episodes to prove it.

CanonPulse is a standalone, platform-independent review system for serialized fiction. A writer submits a full series (up to roughly 300 episodes) and gets back:

- **Real plot holes**, separated from **intentional twists** that the story pays off later.
- **Overdue obligations** — promises the story made and has not yet discharged, weighted by how long a reader will tolerate the wait.
- **A predicted next-episode continuation**, with the features driving that prediction, a named confidence interval, and — critically — an explicit disclosure that the model is fit to a synthetic corpus, not observed reader behaviour (see "Training data" below).
- **Rewrite attribution**: repair a real hole and see the predicted movement, decomposed per edit, with whatever cannot be attributed reported rather than hidden.

Every finding is cited to the episode text that justifies it. Nothing surfaces without an excerpt behind it.

## Why this is not "just another continuity checker"

A naive consistency checker flags every contradiction — intentional or not — because it cannot tell the difference between a plot hole and a twist the author is setting up. CanonPulse resolves that with a dual-layer graph: each narrative claim carries both the episode a reader encounters it in (`perceived_index`) and where it sits in story-time (`true_time`). A contradiction with a later payoff is protected as craft; a contradiction with nothing downstream is flagged as a defect. The resolution step (`app/ledger.py`) is deterministic graph traversal, not a model call, so the same series always yields the same verdict and the result can be argued with.

## Run locally

```bash
uv sync
uv run --group dev pytest
uv run uvicorn app.main:app --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). No credentials or network access are required for the local demo — the bundled series (`data/series/last_monsoon.json`, 220 episodes) and manifest (`data/manifest/last_monsoon.yaml`) are committed data, and the resolver runs entirely offline.

Key endpoints:

- `GET /api/series` — the loaded demo series' metadata.
- `GET /api/audit` — headline counts and every non-`paid` finding, with citations.
- `GET /api/discrimination` — an `EndToEndReport` with **two** separately-labelled numbers, `ledger` and `extracted` (see the honesty section below before reading either one).
- `GET /api/predict?episode=N` — the feature vector for a given episode boundary, **plus** the trained model's predicted continuation (`value`, `lower_ci`, `upper_ci`, `ci_method`, whether the value was `clamped`), and a `disclosure` field repeating that the model is fit to a synthetic corpus. If inference exceeds `INFERENCE_TIMEOUT_SECONDS`, the response instead carries `"degraded": true` and a `fallback` computed by `golden_path()`.
- `POST /api/rewrite` — `{before_episode, after_episode, edits}` → a `RewriteReport`. Both predictions are computed server-side from the same trained predictor, so `total_delta` is never a value the caller supplied — closing the provenance gap a naive "trust the client's delta" design would have. Each edit must name the ledger obligation it discharges; `unattributed` reports whatever movement the named edits don't explain.

## User document ingestion

The committed JSON/YAML series is only the deterministic offline fixture. For
governed uploads, place PDF, DOC/DOCX, JPG/JPEG, PNG, TIFF/TIF, or PPT/PPTX
files in a Unity Catalog Volume and run:

```bash
uv run python scripts/run_document_processing.py \
  --warehouse <warehouse-id> \
  --source-path /Volumes/<catalog>/<volume-schema>/<folder>/ \
  --series-id <series-id> \
  --catalog <catalog> \
  --schema <schema>
```

Databricks `ai_parse_document` creates the governed raw and parsed layers in
`canonpulse_raw_document` and `canonpulse_parsed_document`. CanonPulse then
normalizes the parsed `document.elements` into `EpisodeInput` records in
`app/document_ingestion.py`, retaining source page and element identifiers for
citations. A file named `episode-07.pdf` becomes episode 7; a document with
`Episode 1`/`Episode 2` headings is split by those headings. Ambiguous files
are marked for review instead of being assigned an invented episode number.

Promote a parsed series into the CanonPulse ledger and run governed graph
extraction with:

```bash
uv run python scripts/promote_document_series.py \
  --warehouse <warehouse-id> \
  --series-id <series-id> \
  --title "<series title>" \
  --genre "serialized fiction" \
  --model <serving-endpoint>
```

The runner materializes the long-running model response in
`canonpulse_graph_response` before validating and inserting nodes, excerpts,
ledger entries, and unverified payoff links.

## Training data — read this before trusting a predicted number

**There is no real reader-retention corpus in this repository.** Fetching the real corpora (arXiv 2412.15239, Qidian, Royal Road) needs network access and licensing judgement that is out of scope for this demo. Instead, `app/training_corpus.py` generates a **deterministic, offline, synthetic corpus** shaped like that telemetry would be: each row carries the full structural feature vector plus a `continue_rate` derived from a fully stated formula —

```
continue_rate = clip(
    0.5
    + 0.03 * open_obligation_count   # open threads pull a reader forward
    + 0.02 * mean_urgency            # urgent open threads pull harder
    - 0.08 * overdue_count           # an overdue promise reads as abandoned
    - 0.12 * broken_count            # an unresolved contradiction repels
    + noise,
    0, 1,
)
```

This is grounded in the product's own thesis (see `app/features.py`), not an arbitrary function — but it is still synthetic. A model fit on it demonstrates the pipeline (features → split → fit → held-out error → confidence interval) runs end to end. **It is not evidence that the predicted continuation rate is calibrated to any real audience**, and nothing in this app claims otherwise: every `/api/predict` response repeats this disclosure, and the number never appears on screen looking like a measured retention rate.

The presentation-layer mapping from the model's internal z-score to a displayed rate (`app/predictor.py::_to_probability`) derives its centre and scale from this same synthetic corpus's `continue_rate` distribution, rather than a hardcoded constant, and reports explicitly when it had to clamp. The confidence interval is the empirical 90th percentile of held-out residuals (`CI_METHOD = "p90_held_out_residual"`), not MAE divided by an unexplained constant.

## Offline fallback (`app/demo_mode.py`)

Live demos fail on projector Wi-Fi, not on code. `golden_path()` in `app/demo_mode.py` recomputes the audit for the bundled series through the real `LedgerResolver` — no inference call, no network — and returns the same shape the API returns. `GET /api/predict` wires this up for real: it runs inference in a worker thread with a hard timeout of `INFERENCE_TIMEOUT_SECONDS` (5 seconds), and if that timeout is hit, the response switches to `golden_path()` and marks itself `"degraded": true` before a judge notices. Everything it shows is still computed from committed data through the real ledger; nothing is hardcoded or fabricated. The point of keeping the timeout short is that the fallback degrades the demo to "slightly less live," never to a blank screen or a canned response.

## Databricks deployment prerequisites

None of this is required to run the demo locally. It is required only for the Databricks-hosted path (batched extraction over Delta, the cohort divergence query, and MLflow-tracked training). Nothing below is hardcoded in the repo — every identifier is a parameter you supply:

- A Databricks **workspace URL** and an **authenticated CLI profile** (`databricks auth login --profile <your-profile>`).
- A Unity Catalog **catalog** and **schema** you have permission to create tables in. `sql/ddl.sql` is parameterized with `${catalog}` / `${db}`:
  ```bash
  databricks sql -f sql/ddl.sql --param catalog=<your_catalog> --param db=<your_schema>
  ```
- A **SQL warehouse** to run the DDL and the batched `ai_query` extraction and cohort queries against.
- A **model-serving endpoint** that supports structured/JSON output, passed by name to `app/extraction.py`'s extractor — the extractor never constructs its own connection and never sees or hardcodes warehouse credentials or endpoint IDs.
- An **MLflow experiment** (name or ID) passed to `app/predictor.py::train_and_log`, which logs `held_out_mae`, split strategy, feature order, and the fitted model to that experiment.

Do not put a Databricks token, model API key, or any credential in this repository.

## Demo sequence

1. Load *The Last Monsoon* — 220 episodes.
2. Show baseline flags vs CanonPulse breakdown.
3. Click a protected twist; show the Ep 47 → Ep 218 payoff citation.
4. Show the predicted continuation panel — value, interval, and the synthetic-corpus disclosure.
5. Click "Simulate repair" on a real hole; show the per-edit attributed prediction delta and the unattributed remainder.
6. Show the MLflow run: discrimination precision/recall and held-out MAE.

Cohort-based audience simulation (`app/cohorts.py`) exists and is tested, but is **not** part of the served product or this demo sequence yet — see the honesty section below.

## Honesty section — read this before trusting the discrimination numbers

**The demo series is original and synthetic.** *The Last Monsoon* was generated for this project; it is not a real published work and no claims are made about any specific real series.

**The continuation model trains on a documented synthetic corpus, not platform telemetry.** `app/training_corpus.py` generates it from a stated generative process (see "Training data" above); `app/predictor.py` fits on structural features from that corpus, never on prose. No real reader behavior, retention data, or platform analytics of any kind is used, claimed, or available to this system, and every `/api/predict` response says so directly.

**No real listener or reader data is used or claimed anywhere in this project.** The "cohorts" in `app/cohorts.py` are five fixed, transparent weight vectors over structural features (urgency, fairness, emotional payoff, etc.) — a bounded creative simulation for localizing *where in a series* different reading styles would diverge, not a panel of real people and not a validated audience model. Cohorts are not wired into any served endpoint or the demo sequence; `app/cohorts.py` and its tests exist as a self-contained module, reachable only from tests, until a decision is made to serve them.

**`/api/discrimination` reports two numbers, not one, because a single figure invited exactly the misreading it produced.** An earlier version of this project reported one precision/recall pair computed by resolving the demo series' own pre-populated (`entries`/`payoffs`) graph — data generated *from* the same hand-authored manifest it was scored against, with `app/extraction.py` never in the loop. That number could not fall no matter what the "extraction" did, because no extraction had run. `app/evaluation.py::evaluate_series` now computes both halves explicitly and the dashboard and API never show either without its label:

- **Ledger — recall 1.0, precision 1.0, false-positive rate 0.0.** Given a correct, hand-authored graph, the resolver separates all 6 real plot holes from all 5 intentional twists with no false positives. This measures graph traversal only, not extraction. It is a correctness check on `app/ledger.py`'s deterministic logic, not evidence the system can read fiction.
- **End-to-end — recall 0.0, precision 0.0, false-positive rate 0.0.** Run end-to-end through the offline heuristic extractor (`app/heuristic_extractor.py`, no network, no credentials), the system recovers **0 of 6** real plot holes and protects **0 of 5** intentional twists. It produces 4 contradiction candidates across 220 episodes; 3 of them are matched to a contradiction-class manifest item, but only one (`twist-02`) has *both* endpoints right — the other two match on a single endpoint each, and `twist-02` is an easy case by construction (see below). The 3 clean controls are not over-flagged: they resolve `outstanding`, meaning the extractor found the promise and missed the payoff.

  **The reachable precision ceiling here is 0.55, not 1.0.** Protection requires a *verified* payoff link by design, and no extractor in this repository can emit one — no `Verifier` implementation exists. So `twists_protected` measures the absence of a verifier rather than the extractor, and every twist the extractor correctly locates strictly *lowers* extracted precision. Read `precision 0.00` against 0.55, not against 1.0.

That end-to-end zero is not softened here, and should not be read as a bug to explain away: it is the honest floor for a deliberately naive, rule-based, keyword-and-regex extractor asked to do the hardest part of the pipeline — turning prose it has never seen the answer key for into a graph. Recovering `twist-02` and `twist-05` specifically is weaker evidence than it looks: both were flagged in this project's own review as easy cases by construction (an earlier fixture drew directly from the manifest), so a rule aligning with either of them is expected to fire even on a rule set that generalizes poorly elsewhere. The two-number pair is stronger than the single 1.0 it replaces precisely because it localizes where the difficulty actually lives: traversal is solved; text-to-graph extraction is not, and this repo does not claim otherwise. `HeuristicExtractor` — the offline extractor that produces the end-to-end number above and the only one wired into the served `/api/discrimination` endpoint — was written from the shape of the rules alone and has never seen `data/manifest/last_monsoon.yaml`; `app/llm_extractor.py::LLMExtractor` exists but needs credentials this repo does not have, so it is exercised only offline by `scripts/measure_llm_extraction.py`, never by the served app. `app/manifest.py` enforces the corresponding discipline directly: no test in this repository may assert a discrimination metric equals `1.0`.
