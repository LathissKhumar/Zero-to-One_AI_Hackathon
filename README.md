# CanonPulse

> Every clue, vow, wound, threat, and romance arc is a promise made to a reader. CanonPulse tells a writer which of those promises are broken, which are intentional twists still waiting on their payoff, and which are overdue — with the exact episodes to prove it.

CanonPulse is a standalone, platform-independent review system for serialized fiction. A writer submits a full series (up to roughly 300 episodes) and gets back:

- **Real plot holes**, separated from **intentional twists** that the story pays off later.
- **Overdue obligations** — promises the story made and has not yet discharged, weighted by how long a reader will tolerate the wait.
- **A predicted next-episode continuation**, with the features driving that prediction and a confidence interval.

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
- `GET /api/predict?episode=N` — the feature vector for a given episode boundary.

## Offline fallback (`app/demo_mode.py`)

Live demos fail on projector Wi-Fi, not on code. `golden_path()` in `app/demo_mode.py` recomputes the audit for the bundled series through the real `LedgerResolver` — no inference call, no network — and returns the same shape the API returns. If a live model call would time out (`INFERENCE_TIMEOUT_SECONDS = 5`), the demo switches to this path before a judge notices. Everything it shows is still computed from committed data through the real ledger; nothing is hardcoded or fabricated. The point of keeping the timeout short is that the fallback degrades the demo to "slightly less live," never to a blank screen or a canned response.

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
4. Repair one real hole; show the diff and the attributed prediction delta.
5. Show the cohort × episode divergence map (one `ai_query`).
6. Show the MLflow run: discrimination precision/recall and held-out MAE.

## Honesty section — read this before trusting the discrimination numbers

**The demo series is original and synthetic.** *The Last Monsoon* was generated for this project; it is not a real published work and no claims are made about any specific real series.

**The continuation model trains on public serialized fiction, not platform telemetry.** `app/predictor.py` fits on structural features extracted from the demo corpus. No real reader behavior, retention data, or platform analytics of any kind is used, claimed, or available to this system.

**No real listener or reader data is used or claimed anywhere in this project.** The "cohorts" in `app/cohorts.py` are five fixed, transparent weight vectors over structural features (urgency, fairness, emotional payoff, etc.) — a bounded creative simulation for localizing *where in a series* different reading styles would diverge, not a panel of real people and not a validated audience model.

**On the precision 1.0 / recall 1.0 you will see from `/api/discrimination` on the demo series:** those numbers are real outputs of `score_discrimination()` in `app/manifest.py`, but they are not yet evidence of narrative-understanding accuracy. The demo series was *generated from* the same hand-authored manifest it is scored against, and that generation path bypasses `app/extraction.py` entirely — there is no model call in the loop being measured. What perfect precision and recall demonstrate here is that the resolver and the generator agree on a schema: a planted accidental hole resolves to `broken`, a planted intentional twist resolves to `suspended` with its payoff link intact, and so on. That is a useful correctness check on the ledger logic, and it is exactly what it sounds like: agreement with a script, not a measurement of whether the system can tell twists from holes in fiction it did not help write. Evidence of the latter requires scoring against episodes and manifests the resolver had no part in generating — that evaluation does not exist yet. `app/manifest.py` enforces this directly: no test in this repository may assert a discrimination metric equals `1.0`.
