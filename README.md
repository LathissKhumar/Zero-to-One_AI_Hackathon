# CanonPulse

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
- `GET /api/discrimination` — precision/recall of the resolver against the hand-authored manifest (see the honesty section below before trusting this number).
- `GET /api/predict?episode=N` — the feature vector for a given episode boundary, **plus** the trained model's predicted continuation (`value`, `lower_ci`, `upper_ci`, `ci_method`, whether the value was `clamped`), and a `disclosure` field repeating that the model is fit to a synthetic corpus. If inference exceeds `INFERENCE_TIMEOUT_SECONDS`, the response instead carries `"degraded": true` and a `fallback` computed by `golden_path()`.
- `POST /api/rewrite` — `{before_episode, after_episode, edits}` → a `RewriteReport`. Both predictions are computed server-side from the same trained predictor, so `total_delta` is never a value the caller supplied — closing the provenance gap a naive "trust the client's delta" design would have. Each edit must name the ledger obligation it discharges; `unattributed` reports whatever movement the named edits don't explain.

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

**On the precision 1.0 / recall 1.0 you will see from `/api/discrimination` on the demo series:** those numbers are real outputs of `score_discrimination()` in `app/manifest.py`, but they are not yet evidence of narrative-understanding accuracy. The demo series was *generated from* the same hand-authored manifest it is scored against, and that generation path bypasses `app/extraction.py` entirely — there is no model call in the loop being measured. What perfect precision and recall demonstrate here is that the resolver and the generator agree on a schema: a planted accidental hole resolves to `broken`, a planted intentional twist resolves to `suspended` with its payoff link intact, and so on. That is a useful correctness check on the ledger logic, and it is exactly what it sounds like: agreement with a script, not a measurement of whether the system can tell twists from holes in fiction it did not help write. Evidence of the latter requires scoring against episodes and manifests the resolver had no part in generating — that evaluation does not exist yet. `app/manifest.py` enforces this directly: no test in this repository may assert a discrimination metric equals `1.0`.
