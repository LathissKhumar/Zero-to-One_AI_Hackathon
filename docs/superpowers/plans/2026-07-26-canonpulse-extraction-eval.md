# CanonPulse End-to-End Discrimination Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the discrimination metric measure whether the system can tell twists from holes in a story it did not help write, instead of measuring that the generator and the resolver agree on a schema.

**Architecture:** Today `data/series/last_monsoon.json` ships with `entries` and `payoffs` pre-populated by the same script that was conditioned on the manifest, and `LedgerResolver` simply traverses them — so precision and recall are pinned at 1.0 and `app/extraction.py` never runs. This plan adds a deterministic offline extractor that derives the graph from episode *text*, scores the manifest against that derived graph, and reports two clearly separated numbers: ledger correctness (authored graph) and end-to-end discrimination (extracted graph).

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, pytest. No new dependencies. No network, no credentials.

**Spec:** `docs/superpowers/specs/2026-07-25-canonpulse-dual-layer-graph-design.md`
**Prior plan (fully executed):** `docs/superpowers/plans/2026-07-25-canonpulse-dual-layer-graph.md`

## Why this matters

The README currently has to apologise for its headline metric. The whole-branch review put it plainly: the reported numbers "demonstrate that the resolver and the generator agree on a schema, not that the system understands narrative." A judge who asks "what would make this fail?" gets an admission rather than a demonstration.

After this plan there are two numbers and both are defensible:

- **Ledger correctness** — the authored graph, scored as today. Should stay near-perfect; it measures that traversal is exact.
- **End-to-end discrimination** — the extracted graph. Will be materially below 1.0, and that is the point. It is the number that can fall, which is what makes it evidence.

## Global Constraints

- Python `>=3.11,<3.15`. Run everything through `uv run --group dev`.
- **No new dependencies.** No network access, no credentials, no model calls in any test.
- **The defect manifest is hand-authored ground truth.** Never generate or modify manifest items.
- **No test may assert a quality metric equals `1.0`.** Bound results; never fix them.
- The extractor must be deterministic: same input text always yields the same graph.
- An unverified payoff link must never protect a contradiction. Extracted links start `verified=False`, so extraction-derived twists are *expected* to resolve `broken` unless a verifier approves them — this is the mechanism under test, not a bug to work around.
- The predictor consumes structural features only. Nothing in this plan may add a text-derived feature to `BoundaryFeatures` or `FEATURE_ORDER`.
- Never claim real platform telemetry or listener data.
- Keep the authored-graph headline at `{'baseline_flags': 11, 'real_holes': 6, 'twists_protected': 5, 'overdue_obligations': 3}` with all 20 manifest items on their expected states.
- The suite passes 91 tests today. It must still pass.

## File Structure

**To create:**
| File | Responsibility |
|---|---|
| `app/heuristic_extractor.py` | Derive a graph from episode text by stated rules. Offline, deterministic, imperfect by design |
| `tests/test_heuristic_extractor.py` | Extraction behaviour and determinism |
| `app/evaluation.py` | Score the manifest against either an authored or an extracted graph; report both |
| `tests/test_evaluation.py` | Two-number reporting, and that the extracted number can fall |
| `data/manifest/tide_house.yaml` | Hand-authored ground truth for the adversarial series |
| `data/series/tide_house.json` | Adversarial series, ~40 episodes, defects the Last Monsoon generator never plants |
| `scripts/generate_tide_house.py` | Deterministic offline generator for the adversarial series |

**To modify:** `app/main.py` (report both numbers), `app/static/index.html` + `app.js` (surface both), `README.md` (replace the apology with the two-number framing).

## Task Ordering

Task 1 → Task 2 → Task 3 → Task 4. Task 2 consumes Task 1's extractor; Task 3 needs Task 2's scoring to be meaningful; Task 4 surfaces what Tasks 2 and 3 produce.

---

### Task 1: Heuristic offline extractor

A rule-based extractor that reads episode text and emits a graph. It exists because a real model extractor needs a Databricks workspace, and a `FakeExtractor` that echoes its input cannot make mistakes. This one *can* — that is the requirement, not a shortcoming.

**Files:**
- Create: `app/heuristic_extractor.py`, `tests/test_heuristic_extractor.py`

**Interfaces:**
- Consumes: `app.narrative_models` (`NarrativeNode`, `LedgerEntry`, `PayoffLink`, `Excerpt`, `Series`); `app.extraction.ExtractionResult`
- Produces: `HeuristicExtractor().extract(episodes: list[dict]) -> ExtractionResult`, conforming to the existing `Extractor` protocol

- [ ] **Step 1: Write the failing tests**

> **Corrected after review.** The fixture originally written here paraphrased
> `twist-02` and `twist-05` from `data/manifest/last_monsoon.yaml` — same
> characters, same swim→dive beat, same cassette reveal. Requiring the extractor
> to pass it reintroduced, through the brief, exactly the answer-key circularity
> this plan exists to remove. **The fixture must share no characters, objects or
> beats with any manifest.** Invent an unrelated scenario that still exercises a
> promise being opened, a negated capability later contradicted, and a resolution
> that pays something off. Do not consult a manifest while writing it.

```python
# tests/test_heuristic_extractor.py
from __future__ import annotations

from app.extraction import ExtractionResult
from app.heuristic_extractor import HeuristicExtractor


def episodes() -> list[dict]:
    """Scenario authored independently of every manifest. See the note above:
    a fixture drawn from the answer key silently tunes the extractor to it."""
    ...  # unrelated genre, names and props; see tests/test_heuristic_extractor.py


def test_extraction_conforms_to_the_extractor_protocol():
    result = HeuristicExtractor().extract(episodes())
    assert isinstance(result, ExtractionResult)
    assert result.nodes
    assert result.excerpts


def test_a_node_and_excerpt_exist_for_every_episode():
    result = HeuristicExtractor().extract(episodes())
    assert {node.episode for node in result.nodes} == {1, 3, 20, 30}
    assert {excerpt.episode for excerpt in result.excerpts} == {1, 3, 20, 30}


def test_promise_language_opens_an_obligation():
    result = HeuristicExtractor().extract(episodes())
    promises = [entry for entry in result.entries if entry.kind == "promise"]
    assert promises, "'promises to' should open an obligation"
    assert all(entry.excerpt_ids for entry in promises), "every entry must cite"


def test_extracted_payoff_links_start_unverified():
    """Extraction is untrusted by construction, so an extracted twist resolves
    `broken` until something verifies it. That is the guarantee under test."""
    result = HeuristicExtractor().extract(episodes())
    assert all(link.verified is False for link in result.payoffs)


def test_extraction_is_deterministic():
    first = HeuristicExtractor().extract(episodes())
    second = HeuristicExtractor().extract(episodes())
    assert first.model_dump() == second.model_dump()


def test_empty_input_yields_an_empty_result_without_raising():
    result = HeuristicExtractor().extract([])
    assert result.nodes == [] and result.entries == [] and result.rejected == 0
```

- [ ] **Step 2: Run them red**

Run: `uv run --group dev pytest tests/test_heuristic_extractor.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'app.heuristic_extractor'`.

- [ ] **Step 3: Implement the extractor**

Derive the graph from stated lexical rules. Document every rule in the module docstring — the extractor's *fallibility is the measurement instrument*, so a reader must be able to see exactly what it can and cannot catch.

Required behaviour:
- One `NarrativeNode` and one `Excerpt` per episode, ids stable across runs (`n-{episode}`, `ex-{episode}`).
- Promise detection: obligation-opening language ("promises", "swears", "will return", "one day", "must", an unanswered question). Emit a `promise` entry citing that episode's excerpt.
- Contradiction detection: a negated capability or fact in one episode ("never learned to swim", "cannot", "is dead") followed later by language asserting the opposite ("dives", "swims", "speaks"). Emit a `contradiction` entry whose `episodes` are the two episode numbers, earliest first.
- Payoff detection: resolution language ("finally", "at last", "it was never", "the truth was") emits a `PayoffLink` targeting the most recent unresolved entry that shares a salient noun with the resolving episode.
- `verified` is left `False` on every emitted link.
- Malformed or empty rows increment `rejected` rather than raising.

Do not tune the rules against the manifest. The extractor must be written from the *text*, not from the answer key — tuning it to recover the manifest exactly would recreate the circularity this plan exists to remove.

- [ ] **Step 4: Run them green**

Run: `uv run --group dev pytest tests/test_heuristic_extractor.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/heuristic_extractor.py tests/test_heuristic_extractor.py
git commit -m "feat: add deterministic offline extractor that derives a graph from text"
```

---

### Task 2: Two-number evaluation

**Files:**
- Create: `app/evaluation.py`, `tests/test_evaluation.py`

**Interfaces:**
- Consumes: `app.manifest` (`Manifest`, `DiscriminationReport`, `score_discrimination`, `load_manifest`), `app.ledger.LedgerResolver`, `app.series_loader.load_series`, `app.heuristic_extractor.HeuristicExtractor`
- Produces: `evaluate_series(series, manifest, extractor=None) -> EndToEndReport` with fields `ledger: DiscriminationReport`, `extracted: DiscriminationReport | None`, `extraction_rejected: int`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_evaluation.py
from __future__ import annotations

from pathlib import Path

from app.evaluation import EndToEndReport, evaluate_series
from app.heuristic_extractor import HeuristicExtractor
from app.manifest import load_manifest
from app.series_loader import load_series

SERIES = Path("data/series/last_monsoon.json")
MANIFEST = Path("data/manifest/last_monsoon.yaml")


def test_reports_both_the_authored_and_extracted_scores():
    report = evaluate_series(
        load_series(SERIES), load_manifest(MANIFEST), extractor=HeuristicExtractor()
    )
    assert isinstance(report, EndToEndReport)
    assert report.ledger is not None
    assert report.extracted is not None


def test_the_authored_graph_still_scores_near_perfect():
    """Traversal is exact; this number measures ledger correctness only."""
    report = evaluate_series(load_series(SERIES), load_manifest(MANIFEST))
    assert report.ledger.recall > 0.9
    assert report.extracted is None, "no extractor supplied means no end-to-end number"


def test_the_extracted_score_is_strictly_weaker_than_the_authored_one():
    """The point of the exercise. A rule-based extractor cannot recover a
    hand-authored graph exactly, so this number can fall -- which is what makes
    it evidence rather than a restatement of the fixture."""
    report = evaluate_series(
        load_series(SERIES), load_manifest(MANIFEST), extractor=HeuristicExtractor()
    )
    assert report.extracted.recall < report.ledger.recall


def test_extraction_rejections_are_reported_not_swallowed():
    report = evaluate_series(
        load_series(SERIES), load_manifest(MANIFEST), extractor=HeuristicExtractor()
    )
    assert report.extraction_rejected >= 0
```

- [ ] **Step 2: Run them red**

Run: `uv run --group dev pytest tests/test_evaluation.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'app.evaluation'`.

- [ ] **Step 3: Implement**

`evaluate_series` scores twice:
1. **Ledger** — resolve the series' authored `entries`/`payoffs` and score against the manifest. Identical to today's behaviour.
2. **Extracted** — when an extractor is supplied, rebuild the series' `entries`, `payoffs`, `nodes` and `excerpts` from episode text via the extractor, resolve *that*, and score it against the same manifest.

Episode text comes from the series' own nodes and excerpts, so no new data file is needed.

Extracted entry ids will not match manifest `defect_id`s. Match by position instead: an extracted contradiction counts as recovering a manifest item when its episode span overlaps the item's planted/payoff episodes. Put that matching rule in the docstring — it is the load-bearing judgement in this module, and a reader must be able to disagree with it explicitly rather than discover it by reading code.

- [ ] **Step 4: Run them green**

Run: `uv run --group dev pytest tests/test_evaluation.py -v`

Expected: PASS. Report the two actual numbers in your task report.

- [ ] **Step 5: Commit**

```bash
git add app/evaluation.py tests/test_evaluation.py
git commit -m "feat: score discrimination end to end through extraction, not just traversal"
```

---

### Task 3: Adversarial series

A second series the Last Monsoon generator did not produce, so the resolver faces defect shapes it was not built around.

**Files:**
- Create: `data/manifest/tide_house.yaml`, `scripts/generate_tide_house.py`, `data/series/tide_house.json`
- Modify: `tests/test_evaluation.py`

**Interfaces:**
- Produces: a `Series` loadable by `load_series`, and a `Manifest` loadable by `load_manifest`

- [ ] **Step 1: Hand-author the manifest**

**Human task. Do not generate it with a model.** ~40 episodes, 12 labelled items, deliberately including shapes Last Monsoon does not contain:
- a contradiction whose payoff lands only *one* episode later (tests `MIN_PAYOFF_GAP` at its boundary)
- two contradictions sharing a single payoff episode
- a promise paid off by an episode that also opens a new contradiction
- a red herring: resolution-sounding language that resolves nothing
- at least 3 clean controls

Write it to `data/manifest/tide_house.yaml` in the same schema as `data/manifest/last_monsoon.yaml`.

- [ ] **Step 2: Write the generator and the failing test**

```python
# Append to tests/test_evaluation.py
TIDE_SERIES = Path("data/series/tide_house.json")
TIDE_MANIFEST = Path("data/manifest/tide_house.yaml")


def test_the_adversarial_series_resolves_to_its_own_ground_truth():
    from app.ledger import LedgerResolver

    series = load_series(TIDE_SERIES)
    manifest = load_manifest(TIDE_MANIFEST)
    states = {item.entry.id: item.state for item in LedgerResolver().resolve_series(series)}
    mismatches = [
        item.defect_id
        for item in manifest.items
        if states.get(item.defect_id) != item.expected_state
    ]
    assert not mismatches, f"authored graph disagrees with its manifest: {mismatches}"


def test_extraction_scores_lower_on_the_adversarial_series():
    """Shapes the Last Monsoon generator never produces should cost the
    extractor more, not less."""
    monsoon = evaluate_series(
        load_series(SERIES), load_manifest(MANIFEST), extractor=HeuristicExtractor()
    )
    tide = evaluate_series(
        load_series(TIDE_SERIES), load_manifest(TIDE_MANIFEST), extractor=HeuristicExtractor()
    )
    assert tide.extracted.recall <= monsoon.extracted.recall
```

- [ ] **Step 3: Run them red**

Run: `uv run --group dev pytest tests/test_evaluation.py -v`

Expected: FAIL — `data/series/tide_house.json` does not exist.

- [ ] **Step 4: Generate the series**

`scripts/generate_tide_house.py`, deterministic and offline, same shape as `scripts/generate_series.py`. ~40 episodes, all with full text (short — 150–300 words each). Conditioned on the hand-authored manifest, using a **different prompt/authoring path** than the analyzer.

Regenerating twice must produce byte-identical output.

- [ ] **Step 5: Run them green**

Run: `uv run --group dev pytest -q`

Expected: PASS, with the Last Monsoon headline unchanged.

- [ ] **Step 6: Commit**

```bash
git add data/manifest/tide_house.yaml data/series/tide_house.json scripts/generate_tide_house.py tests/test_evaluation.py
git commit -m "feat: add an adversarial series the demo generator did not produce"
```

---

### Task 4: Surface both numbers

**Files:**
- Modify: `app/main.py`, `app/static/index.html`, `app/static/app.js`, `README.md`, `tests/test_api_v2.py`

**Interfaces:**
- Consumes: `app.evaluation.evaluate_series`
- Produces: `GET /api/discrimination` returning both numbers

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_api_v2.py
def test_discrimination_reports_ledger_and_end_to_end_separately(client):
    """One number measures traversal, the other measures the whole pipeline.
    Reporting a single figure invites a judge to read the wrong one as both."""
    payload = client.get("/api/discrimination").json()
    assert "ledger" in payload
    assert "extracted" in payload
    assert payload["extracted"]["recall"] < payload["ledger"]["recall"]
```

- [ ] **Step 2: Run it red**

Run: `uv run --group dev pytest tests/test_api_v2.py::test_discrimination_reports_ledger_and_end_to_end_separately -v`

Expected: FAIL — the endpoint returns a flat `DiscriminationReport`.

- [ ] **Step 3: Implement**

Change `/api/discrimination` to return the `EndToEndReport`. Compute once at startup like `_predictor()`, not per request.

In the UI, show both with labels that say what each measures — "ledger traversal" and "end to end, from text". Do not show them adjacent without labels; an unlabelled pair invites the reader to assume the higher one is the headline.

- [ ] **Step 4: Rewrite the README's honesty section**

The section currently apologises for a number that cannot fall. Replace it with the two-number framing: ledger correctness is near-perfect and measures traversal exactness; end-to-end discrimination is materially lower and measures whether the system recovers structure from text it did not help author. Keep the disclosure that the demo series and training corpus are synthetic.

- [ ] **Step 5: Run green and verify live**

Run: `uv run --group dev pytest -q`, then start the server and fetch `/api/discrimination` and `/`. Confirm both numbers render with their labels. Kill the server.

- [ ] **Step 6: Commit**

```bash
git add app/main.py app/static README.md tests/test_api_v2.py
git commit -m "feat: report ledger correctness and end-to-end discrimination separately"
```

---

## Plan Self-Review

**Spec coverage.** The spec's evaluation section requires metrics "measured against ground truth the analyzer never sees". Task 1 supplies an analyzer that has not seen the answer key; Task 2 scores against it; Task 3 supplies ground truth from a different generator; Task 4 stops the two numbers being conflated.

**Placeholder scan.** No TBD or "similar to Task N". Every code step contains complete runnable code. Task 1 Step 3 and Task 3 Step 4 specify behaviour rather than literal code because the extractor's rules and the adversarial prose are authoring work, not transcription — the tests pin the contract in both cases.

**Type consistency.** `ExtractionResult`, `Series`, `Manifest`, `DiscriminationReport` are used with the field names defined in the committed modules. `evaluate_series` and `EndToEndReport` are used consistently across Tasks 2, 3 and 4.

**Known risk.** Task 2's `test_the_extracted_score_is_strictly_weaker_than_the_authored_one` will fail if the heuristic extractor happens to recover the graph perfectly. That would mean the extractor was tuned to the answer key, which Task 1 Step 3 forbids — so the failure is informative, and the fix is to weaken the tuning, never to weaken the assertion.

**Review correction, carried into Task 4.** The original Task 1 fixture was drawn
from the manifest (see the note in Task 1 Step 1). Even after correcting it, any
extractor rule that happens to align with `twist-02` or `twist-05` should be
treated as an easy case by construction. When Task 4 reports the end-to-end
number, say which manifest items the extractor recovers — a clean recovery of
those two specifically is weaker evidence than recovery of the other nine.
