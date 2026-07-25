# CanonPulse Dual-Layer Graph Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a review system that ingests a serialized series of up to 300 episodes, separates intentional twists from real plot holes with cited evidence, and predicts next-episode continuation from structural features alone.

**Architecture:** A model extracts a dual-layer narrative graph (`G_true` chronological, `G_perceived` presentation order) from episode text via one batched `ai_query`. Deterministic traversal resolves every discrepancy into suspended / broken / paid / outstanding. Structural features derived from that ledger feed a regressor trained on public serial-fiction retention data. The predictor never sees prose, so a rewrite can only move the score by changing structure.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, scikit-learn, MLflow, pytest, Databricks (Delta, Unity Catalog, Vector Search, `ai_query`, Model Serving, Apps), vanilla HTML/CSS/JS.

**Spec:** `docs/superpowers/specs/2026-07-25-canonpulse-dual-layer-graph-design.md`
**Schedule and lane assignments:** `canonpulse-16h-plan.md`

## Global Constraints

- Python `>=3.11,<3.15`. Run everything through `uv run --group dev`.
- **No text-derived feature may be added to `BoundaryFeatures`.** Structural only.
- **No feature may read episodes after its boundary.** Enforced by test in Task 3.
- **No test may assert a quality metric equals `1.0`.** Bound results (`> 0.7`); never fix them.
- The defect manifest is hand-authored and withheld from the analyzer. Never generate it.
- An unverified payoff link must never protect a contradiction.
- 100% of product inference runs on Databricks Foundation Model APIs. The direct OpenAI key is cold failover only.
- Parameterize catalog, schema, warehouse, model endpoint, index, experiment. No hardcoded IDs or credentials.
- Never claim real platform telemetry, real listener data, or validated retention uplift. State that the demo series is original and the training corpus is public serialized fiction.
- Every ledger claim surfaced to a user carries at least one `Excerpt` citation.

## File Structure

**Already scaffolded and committed** (do not recreate):
- `app/narrative_models.py` — domain types
- `app/ledger.py` — `LedgerResolver`, `LedgerSummary`
- `app/features.py` — `FeatureExtractor`
- `sql/ddl.sql` — Unity Catalog schema

**To create:**
| File | Responsibility |
|---|---|
| `tests/test_ledger.py` | Discrimination behaviour, state by state |
| `tests/test_features.py` | No-lookahead invariant, feature values |
| `app/manifest.py` | Defect manifest types, loader, discrimination scoring |
| `tests/test_manifest.py` | Scoring correctness against a known manifest |
| `data/manifest/last_monsoon.yaml` | Hand-authored ground truth (20 items) |
| `data/series/last_monsoon.json` | 220-episode demo series, generated once, committed |
| `app/series_loader.py` | Load + validate series JSON against manifest |
| `app/extraction.py` | Episode text → graph. `Extractor` protocol + Databricks and fake impls |
| `tests/test_extraction.py` | Fake extractor contract, malformed-row handling |
| `app/predictor.py` | Feature vector → continuation prediction. Train + serve |
| `tests/test_predictor.py` | Grouped split, no leakage, prediction shape |
| `app/corpus.py` | Training corpus ingest and within-book normalization |
| `tests/test_corpus.py` | Z-scoring, grouped split by `book_id` |
| `app/cohorts.py` | Cohort × episode reactions, blind to variant |
| `tests/test_cohorts.py` | Blinding, one-statement batching |
| `app/rewrite.py` | Surgical repair + per-edit attribution |
| `tests/test_rewrite.py` | Attribution sums to the delta |
| `app/static/*` | Comparison screen, attribution table, heatmap |
| `sql/extract_graph.sql` | Batched `ai_query` extraction |
| `sql/cohort_reactions.sql` | Batched `ai_query` cohort pass |

**To delete** (Task 11): `app/engine.py`, `app/demo_data.py`, `app/models.py`, `tests/test_engine.py`, `tests/test_benchmark.py`, `tests/test_discovery.py`, `sql/audience_court.sql`.

## Dependency Graph

```
Task 1 (ledger tests) ─┬─► Task 4 (extraction) ─► Task 8 (cohorts)
                       ├─► Task 5 (manifest+eval)
                       └─► Task 9 (rewrite)
Task 2 (demo series) ──┴─► Task 5
Task 3 (feature tests) ──► Task 7 (predictor) ──► Task 9
Task 6 (corpus) ─────────► Task 7
Task 10 (API) ──► Task 11 (UI) ──► Task 12 (hardening)
```

Lane A (data/model): Tasks 3, 6, 7. Lane B (graph/agents): Tasks 1, 2, 4, 5, 8, 9. Lane C (platform/UI): Tasks 10, 11, 12.

---

### Task 1: Ledger discrimination tests

The scaffolded `app/ledger.py` has no tests. This is the product's core claim, so it gets covered first.

**Files:**
- Create: `tests/test_ledger.py`

**Interfaces:**
- Consumes: `LedgerResolver.resolve_series(series: Series, as_of: int | None) -> list[ResolvedEntry]`; `LedgerSummary(resolved).headline() -> dict[str, int]`
- Produces: `build_series(**overrides) -> Series` test helper, reused by Tasks 3 and 5.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ledger.py
from __future__ import annotations

import pytest

from app.ledger import LedgerResolver, LedgerSummary
from app.narrative_models import Excerpt, LedgerEntry, NarrativeNode, PayoffLink, Series


def build_series(
    entries: list[LedgerEntry] | None = None,
    payoffs: list[PayoffLink] | None = None,
    total_episodes: int = 60,
) -> Series:
    """Minimal series with one contradiction and one promise, both unpaid."""
    default_entries = [
        LedgerEntry(
            id="c-1",
            kind="contradiction",
            description="Tara cannot swim in Ep 3 but dives in Ep 20.",
            episodes=[3, 20],
            excerpt_ids=["ex-3", "ex-20"],
            entities=["Tara"],
        ),
        LedgerEntry(
            id="p-1",
            kind="promise",
            description="The cassette must be played when the rain returns.",
            episodes=[1],
            excerpt_ids=["ex-1"],
            urgency=3,
            promise_kind="mystery",
            entities=["Asha"],
        ),
    ]
    return Series(
        id="test-series",
        title="Test Series",
        genre="thriller",
        total_episodes=total_episodes,
        nodes=[
            NarrativeNode(id="n-30", episode=30, perceived_index=30, summary="Reveal", excerpt_id="ex-30"),
        ],
        entries=entries if entries is not None else default_entries,
        payoffs=payoffs or [],
        excerpts=[
            Excerpt(id="ex-1", episode=1, text="PLAY THIS ONLY WHEN THE RAIN RETURNS."),
            Excerpt(id="ex-3", episode=3, text="Tara never learned to swim."),
            Excerpt(id="ex-20", episode=20, text="Tara dives into the channel."),
            Excerpt(id="ex-30", episode=30, text="'I was never in the water. You saw what you needed to see.'"),
        ],
    )


def resolve_one(entry_id: str, series: Series, **kwargs):
    resolved = LedgerResolver(**kwargs).resolve_series(series)
    return next(item for item in resolved if item.entry.id == entry_id)


def test_contradiction_with_downstream_payoff_is_protected():
    series = build_series(
        payoffs=[PayoffLink(node_id="n-30", target_id="c-1", episode=30, rationale="Reveals the dive was imagined.")]
    )
    result = resolve_one("c-1", series)
    assert result.state == "suspended"
    assert result.is_protected
    assert not result.is_defect
    assert result.payoff.episode == 30
    assert "Ep 30" in result.reason


def test_contradiction_without_payoff_is_a_defect():
    result = resolve_one("c-1", build_series())
    assert result.state == "broken"
    assert result.is_defect
    assert result.citations, "a defect must cite the conflicting claims"


def test_promise_with_payoff_is_paid():
    series = build_series(
        payoffs=[PayoffLink(node_id="n-30", target_id="p-1", episode=30, rationale="The cassette plays.")]
    )
    assert resolve_one("p-1", series).state == "paid"


def test_promise_within_grace_is_open_but_not_overdue():
    # urgency 3 -> 40-episode grace; planted Ep 1, horizon Ep 30 -> age 29.
    result = resolve_one("p-1", build_series(total_episodes=30))
    assert result.state == "outstanding"
    assert result.overdue is False


def test_promise_past_grace_is_overdue():
    # age 79 exceeds the 40-episode window for urgency 3.
    result = resolve_one("p-1", build_series(total_episodes=80))
    assert result.state == "outstanding"
    assert result.overdue is True
    assert "past" in result.reason


def test_payoff_in_the_same_episode_does_not_protect():
    """Extraction noise: a reveal cannot discharge a claim the audience is still hearing."""
    series = build_series(
        payoffs=[PayoffLink(node_id="n-30", target_id="c-1", episode=20, rationale="same-episode noise")]
    )
    assert resolve_one("c-1", series).state == "broken"


def test_rejected_verifier_leaves_the_contradiction_broken():
    """A hallucinated payoff must never suppress a real defect."""
    series = build_series(
        payoffs=[PayoffLink(node_id="n-30", target_id="c-1", episode=30, rationale="invented")]
    )
    result = resolve_one("c-1", series, verifier=lambda link, entry: False)
    assert result.state == "broken"


def test_as_of_horizon_hides_later_payoffs():
    series = build_series(
        payoffs=[PayoffLink(node_id="n-30", target_id="c-1", episode=30, rationale="Late reveal.")]
    )
    early = LedgerResolver().resolve_series(series, as_of=25)
    assert next(item for item in early if item.entry.id == "c-1").state == "broken"


def test_summary_headline_separates_baseline_from_real_defects():
    series = build_series(
        payoffs=[PayoffLink(node_id="n-30", target_id="c-1", episode=30, rationale="Reveal.")]
    )
    summary = LedgerSummary(LedgerResolver().resolve_series(series))
    headline = summary.headline()
    assert headline["twists_protected"] == 1
    assert headline["real_holes"] == 0
    # The gap between these two numbers is the product.
    assert headline["baseline_flags"] == 1
```

- [ ] **Step 2: Run to verify they fail or pass honestly**

Run: `uv run --group dev pytest tests/test_ledger.py -v`

Expected: all PASS. `app/ledger.py` already exists, so this task verifies the scaffold rather than driving new code. **If any test fails, fix `app/ledger.py` — not the test.** The tests encode the spec.

- [ ] **Step 3: Commit**

```bash
git add tests/test_ledger.py
git commit -m "test: cover twist-vs-hole discrimination in the ledger"
```

---

### Task 2: Demo series and defect manifest

**Files:**
- Create: `data/manifest/last_monsoon.yaml`, `data/series/last_monsoon.json`, `app/series_loader.py`, `tests/test_series_loader.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: `load_series(path: Path) -> Series`; `load_manifest(path: Path) -> Manifest` (type defined in Task 5)

- [ ] **Step 1: Add the YAML dependency**

```toml
# pyproject.toml -- add to [project] dependencies
dependencies = [
  "fastapi>=0.115,<1",
  "pydantic>=2.9,<3",
  "uvicorn[standard]>=0.30,<1",
  "pyyaml>=6.0,<7",
]
```

Run: `uv sync`

- [ ] **Step 2: Hand-author the manifest**

**This is a human task. Do not generate it with a model.** 20 items. Each `defect_id` must be unique; `planted_episode` and `payoff_episode` must be consistent with the arc you intend.

```yaml
# data/manifest/last_monsoon.yaml
series_id: last-monsoon
authored_by: team
items:
  # --- 6 accidental holes: contradiction, no payoff anywhere ---
  - defect_id: hole-01
    defect_class: accidental_hole
    planted_episode: 12
    payoff_episode: null
    expected_state: broken
    notes: "Ep 12 says the ferry sank at dawn; Ep 88 says it sank at night. Never reconciled."
  - defect_id: hole-02
    defect_class: accidental_hole
    planted_episode: 34
    payoff_episode: null
    expected_state: broken
    notes: "Rafi's brother is named Imran in Ep 34, Irfan in Ep 101."
  - defect_id: hole-03
    defect_class: accidental_hole
    planted_episode: 47
    payoff_episode: null
    expected_state: broken
    notes: "Asha's phone is destroyed Ep 47, used without explanation Ep 52."
  - defect_id: hole-04
    defect_class: accidental_hole
    planted_episode: 90
    payoff_episode: null
    expected_state: broken
    notes: "The locket is described as brass in Ep 2 and silver in Ep 90."
  - defect_id: hole-05
    defect_class: accidental_hole
    planted_episode: 140
    payoff_episode: null
    expected_state: broken
    notes: "Inspector Rao retires in Ep 140 but leads the raid in Ep 160."
  - defect_id: hole-06
    defect_class: accidental_hole
    planted_episode: 175
    payoff_episode: null
    expected_state: broken
    notes: "Tara's scar switches arms between Ep 175 and Ep 190."

  # --- 5 intentional twists: contradiction-shaped, payoff downstream ---
  - defect_id: twist-01
    defect_class: intentional_twist
    planted_episode: 47
    payoff_episode: 218
    expected_state: suspended
    notes: "Unreliable narrator. Asha's account of the fire is wrong; Ep 218 reveals she was not there. 171-episode span -- this is the hero citation."
  - defect_id: twist-02
    defect_class: intentional_twist
    planted_episode: 3
    payoff_episode: 134
    expected_state: suspended
    notes: "Tara cannot swim (Ep 3) yet dives (Ep 60). Ep 134 reveals the dive was Meera, not Tara."
  - defect_id: twist-03
    defect_class: intentional_twist
    planted_episode: 22
    payoff_episode: 178
    expected_state: suspended
    notes: "Flashback misreadable as present tense. Ep 178 dates it to 2009."
  - defect_id: twist-04
    defect_class: intentional_twist
    planted_episode: 66
    payoff_episode: 199
    expected_state: suspended
    notes: "Identity reveal: the informant and the victim's sister are one person."
  - defect_id: twist-05
    defect_class: intentional_twist
    planted_episode: 110
    payoff_episode: 210
    expected_state: suspended
    notes: "The cassette's voice is not the father's. Contradicts Ep 1 framing until Ep 210."

  # --- 6 outstanding obligations: planted, unpaid at Ep 220 ---
  - defect_id: open-01
    defect_class: outstanding_obligation
    planted_episode: 5
    payoff_episode: null
    expected_state: outstanding
    notes: "Overdue. Urgency 5, planted Ep 5, open at 220."
  - defect_id: open-02
    defect_class: outstanding_obligation
    planted_episode: 30
    payoff_episode: null
    expected_state: outstanding
    notes: "Overdue. Urgency 4."
  - defect_id: open-03
    defect_class: outstanding_obligation
    planted_episode: 71
    payoff_episode: null
    expected_state: outstanding
    notes: "Overdue. Urgency 4."
  - defect_id: open-04
    defect_class: outstanding_obligation
    planted_episode: 205
    payoff_episode: null
    expected_state: outstanding
    notes: "Healthy. Urgency 3, planted recently."
  - defect_id: open-05
    defect_class: outstanding_obligation
    planted_episode: 212
    payoff_episode: null
    expected_state: outstanding
    notes: "Healthy. Urgency 4."
  - defect_id: open-06
    defect_class: outstanding_obligation
    planted_episode: 218
    payoff_episode: null
    expected_state: outstanding
    notes: "Healthy. Urgency 5, planted two episodes before the horizon."

  # --- 3 clean controls: nothing wrong. Measures false-positive rate ---
  - defect_id: clean-01
    defect_class: clean_control
    planted_episode: 40
    payoff_episode: 55
    expected_state: paid
    notes: "Ordinary plant and payoff. Must not be flagged."
  - defect_id: clean-02
    defect_class: clean_control
    planted_episode: 120
    payoff_episode: 133
    expected_state: paid
    notes: "Ordinary plant and payoff."
  - defect_id: clean-03
    defect_class: clean_control
    planted_episode: 180
    payoff_episode: 195
    expected_state: paid
    notes: "Ordinary plant and payoff."
```

- [ ] **Step 3: Generate the series conditioned on the manifest**

**Use a different prompt path than the analyzer.** Two stages — a one-shot generation of 220 beats produces incoherent mush.

Stage 1, arc skeleton: prompt a model for acts, turning points, and character threads for a 220-episode Mumbai thriller, passing the manifest's plant and payoff episode numbers as fixed constraints.

Stage 2, beats: for each episode, generate a 2–4 sentence beat conditioned on the skeleton plus any manifest item anchored to that episode. Write full text (600–1200 words) for Ep 1, 12, 47, 88, 134, 178, 199, 210, 218, 220.

Emit `data/series/last_monsoon.json` matching the `Series` schema. Commit it — generation runs once, not per test.

- [ ] **Step 4: Write the failing loader test**

```python
# tests/test_series_loader.py
from __future__ import annotations

from pathlib import Path

from app.series_loader import load_series

SERIES_PATH = Path("data/series/last_monsoon.json")


def test_demo_series_spans_two_hundred_plus_episodes():
    series = load_series(SERIES_PATH)
    assert series.total_episodes == 220
    assert series.id == "last-monsoon"


def test_every_entry_cites_an_existing_excerpt():
    series = load_series(SERIES_PATH)
    known = {excerpt.id for excerpt in series.excerpts}
    for entry in series.entries:
        assert entry.excerpt_ids, f"{entry.id} has no citation"
        for excerpt_id in entry.excerpt_ids:
            assert excerpt_id in known, f"{entry.id} cites unknown excerpt {excerpt_id}"


def test_payoff_links_point_at_real_entries():
    series = load_series(SERIES_PATH)
    known = {entry.id for entry in series.entries}
    for link in series.payoffs:
        assert link.target_id in known, f"payoff targets unknown entry {link.target_id}"
```

- [ ] **Step 5: Run it red**

Run: `uv run --group dev pytest tests/test_series_loader.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'app.series_loader'`.

- [ ] **Step 6: Implement the loader**

```python
# app/series_loader.py
"""Load and validate the demo series.

Validation is not ceremony: a dangling excerpt reference means a warning would
surface to a writer with no evidence behind it, which is the one thing this
product must never do.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.narrative_models import Series


def load_series(path: Path) -> Series:
    with path.open(encoding="utf-8") as handle:
        return Series.model_validate(json.load(handle))
```

- [ ] **Step 7: Run it green**

Run: `uv run --group dev pytest tests/test_series_loader.py -v`

Expected: PASS. If citations dangle, fix the generated JSON — not the test.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock app/series_loader.py tests/test_series_loader.py data/
git commit -m "feat: add hand-authored defect manifest and 220-episode demo series"
```

---

### Task 3: Feature extraction tests and the no-lookahead invariant

**Files:**
- Create: `tests/test_features.py`

**Interfaces:**
- Consumes: `FeatureExtractor().extract(series: Series, episode: int) -> BoundaryFeatures`; `build_series` from `tests/test_ledger.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_features.py
from __future__ import annotations

from app.features import FeatureExtractor
from app.narrative_models import PayoffLink
from tests.test_ledger import build_series


def test_features_ignore_everything_after_the_boundary():
    """The no-lookahead invariant, in executable form.

    A feature that consults later episodes inflates offline metrics and collapses
    in production, so this test guards the whole feature module.
    """
    series = build_series(total_episodes=60)
    baseline = FeatureExtractor().extract(series, episode=10)

    mutated = series.model_copy(deep=True)
    mutated.payoffs.append(
        PayoffLink(node_id="n-30", target_id="p-1", episode=30, rationale="later payoff")
    )
    after = FeatureExtractor().extract(mutated, episode=10)

    assert after == baseline


def test_open_obligations_are_counted_at_the_boundary():
    features = FeatureExtractor().extract(build_series(total_episodes=60), episode=10)
    assert features.open_obligation_count == 1
    assert features.mean_urgency == 3.0
    assert features.max_obligation_age == 9  # planted Ep 1, boundary Ep 10


def test_paid_obligations_drop_out_of_the_open_count():
    series = build_series(
        payoffs=[PayoffLink(node_id="n-30", target_id="p-1", episode=30, rationale="paid")],
        total_episodes=60,
    )
    assert FeatureExtractor().extract(series, episode=40).open_obligation_count == 0


def test_overdue_count_rises_past_the_grace_window():
    series = build_series(total_episodes=200)
    assert FeatureExtractor().extract(series, episode=20).overdue_count == 0
    assert FeatureExtractor().extract(series, episode=100).overdue_count == 1


def test_feature_vector_excludes_the_episode_index():
    """Episode number is bookkeeping, not signal -- training on it would let the
    model memorise position rather than structure."""
    vector = FeatureExtractor().extract(build_series(), episode=10).to_vector()
    assert "episode" not in vector
    assert all(isinstance(value, float) for value in vector.values())
```

- [ ] **Step 2: Run to verify**

Run: `uv run --group dev pytest tests/test_features.py -v`

Expected: all PASS against the scaffolded `app/features.py`. **If any fail, fix `app/features.py`.**

- [ ] **Step 3: Commit**

```bash
git add tests/test_features.py
git commit -m "test: lock the no-lookahead invariant on boundary features"
```

---

### Task 4: Batched graph extraction

**Files:**
- Create: `app/extraction.py`, `tests/test_extraction.py`, `sql/extract_graph.sql`

**Interfaces:**
- Produces: `Extractor` protocol with `extract(episodes: list[dict]) -> ExtractionResult`; `FakeExtractor` for tests; `DatabricksExtractor(warehouse, model, catalog, schema)`; `ExtractionResult(nodes, entries, payoffs, excerpts, rejected)`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_extraction.py
from __future__ import annotations

from app.extraction import ExtractionResult, FakeExtractor, parse_extraction_row


def test_fake_extractor_returns_a_usable_graph():
    result = FakeExtractor().extract([{"episode": 1, "synopsis": "Asha finds a cassette."}])
    assert isinstance(result, ExtractionResult)
    assert result.nodes
    assert result.rejected == 0


def test_malformed_rows_are_rejected_without_killing_the_batch():
    """A partial graph degrades the verdict; a crash loses the whole series."""
    rows = [
        '{"nodes": [{"id": "n-1", "episode": 1, "perceived_index": 1, "summary": "ok"}]}',
        "not json at all",
        '{"nodes": [{"id": "n-2", "episode": 2, "perceived_index": 2, "summary": "ok"}]}',
    ]
    parsed = [parse_extraction_row(row) for row in rows]
    assert sum(1 for item in parsed if item is None) == 1
    assert sum(1 for item in parsed if item is not None) == 2


def test_payoff_links_start_unverified():
    """Protection requires verification; trusting the extractor by default would
    let a hallucinated payoff suppress a real defect."""
    result = FakeExtractor().extract([{"episode": 1, "synopsis": "Asha finds a cassette."}])
    assert all(link.verified is False for link in result.payoffs)
```

- [ ] **Step 2: Run it red**

Run: `uv run --group dev pytest tests/test_extraction.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'app.extraction'`.

- [ ] **Step 3: Implement extraction**

```python
# app/extraction.py
"""Episode text -> dual-layer graph.

The only model-driven path into the ledger. Everything downstream is
deterministic, so extraction quality is the system's ceiling.

Runs as one batched ai_query over Delta rows rather than N sequential calls --
at 300 episodes that difference is what makes series-scale analysis tractable.
"""

from __future__ import annotations

import json
from typing import Protocol

from pydantic import BaseModel, Field

from app.narrative_models import Excerpt, LedgerEntry, NarrativeNode, PayoffLink


class ExtractionResult(BaseModel):
    nodes: list[NarrativeNode] = Field(default_factory=list)
    entries: list[LedgerEntry] = Field(default_factory=list)
    payoffs: list[PayoffLink] = Field(default_factory=list)
    excerpts: list[Excerpt] = Field(default_factory=list)
    rejected: int = 0


class Extractor(Protocol):
    def extract(self, episodes: list[dict]) -> ExtractionResult: ...


def parse_extraction_row(raw: str) -> dict | None:
    """Parse one model response. Returns None on malformed output.

    Models occasionally emit prose around JSON or truncate mid-object. Dropping
    the row keeps the batch alive; the resulting graph is partial, which the
    ledger handles, rather than absent, which it does not.
    """
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


class FakeExtractor:
    """Deterministic extractor for tests and offline demo mode."""

    def extract(self, episodes: list[dict]) -> ExtractionResult:
        nodes: list[NarrativeNode] = []
        excerpts: list[Excerpt] = []
        for row in episodes:
            episode = int(row["episode"])
            text = row.get("synopsis") or row.get("body") or ""
            nodes.append(
                NarrativeNode(
                    id=f"n-{episode}",
                    episode=episode,
                    perceived_index=episode,
                    summary=text[:200],
                    excerpt_id=f"ex-{episode}",
                )
            )
            excerpts.append(Excerpt(id=f"ex-{episode}", episode=episode, text=text))
        return ExtractionResult(nodes=nodes, excerpts=excerpts)


class DatabricksExtractor:
    """Batched ai_query extraction over a Delta episodes table."""

    def __init__(self, connection, catalog: str, schema: str, model: str) -> None:
        self._connection = connection
        self._catalog = catalog
        self._schema = schema
        self._model = model

    def extract(self, episodes: list[dict]) -> ExtractionResult:
        sql = (
            Path(__file__).parent.parent / "sql" / "extract_graph.sql"
        ).read_text(encoding="utf-8")
        statement = (
            sql.replace("${catalog}", self._catalog)
            .replace("${db}", self._schema)
            .replace("${model}", self._model)
        )
        with self._connection.cursor() as cursor:
            cursor.execute(statement)
            rows = cursor.fetchall()

        result = ExtractionResult()
        for row in rows:
            parsed = parse_extraction_row(row[0])
            if parsed is None:
                result.rejected += 1
                continue
            result.nodes.extend(NarrativeNode.model_validate(item) for item in parsed.get("nodes", []))
            result.entries.extend(LedgerEntry.model_validate(item) for item in parsed.get("entries", []))
            result.payoffs.extend(PayoffLink.model_validate(item) for item in parsed.get("payoffs", []))
            result.excerpts.extend(Excerpt.model_validate(item) for item in parsed.get("excerpts", []))
        return result
```

Add `from pathlib import Path` to the imports.

- [ ] **Step 4: Write the extraction SQL**

```sql
-- sql/extract_graph.sql
-- One statement extracts the graph for an entire series. At 300 episodes this
-- replaces 300 sequential API calls with a single governed, parallel job.
SELECT
  episode,
  ai_query(
    '${model}',
    concat(
      'Extract narrative structure as JSON. Return keys: nodes, entries, payoffs, excerpts. ',
      'A node has id, episode, perceived_index, true_time (0-1 chronological position or null), ',
      'summary, entities, valence (-1..1), excerpt_id. ',
      'An entry has id, kind (contradiction|promise), description, episodes, excerpt_ids, urgency (1-5), entities. ',
      'A payoff has node_id, target_id, episode, rationale. ',
      'Episode ', CAST(episode AS STRING), ': ', coalesce(body, synopsis)
    )
  ) AS extraction
FROM ${catalog}.${db}.episodes
WHERE series_id = :series_id
ORDER BY episode;
```

- [ ] **Step 5: Run it green**

Run: `uv run --group dev pytest tests/test_extraction.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/extraction.py tests/test_extraction.py sql/extract_graph.sql
git commit -m "feat: add batched ai_query graph extraction with row-level fallback"
```

---

### Task 5: Discrimination evaluation against the manifest

Replaces the superseded `run_benchmark`, which was circular by construction.

**Files:**
- Create: `app/manifest.py`, `tests/test_manifest.py`

**Interfaces:**
- Consumes: `LedgerResolver.resolve_series`, `load_series`
- Produces: `Manifest`, `ManifestItem`, `load_manifest(path) -> Manifest`, `score_discrimination(manifest, resolved) -> DiscriminationReport`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_manifest.py
from __future__ import annotations

from pathlib import Path

from app.manifest import DiscriminationReport, ManifestItem, load_manifest, score_discrimination
from app.narrative_models import LedgerEntry, ResolvedEntry

MANIFEST_PATH = Path("data/manifest/last_monsoon.yaml")


def resolved(entry_id: str, state: str, overdue: bool = False) -> ResolvedEntry:
    return ResolvedEntry(
        entry=LedgerEntry(id=entry_id, kind="contradiction", description="", episodes=[1]),
        state=state,
        overdue=overdue,
    )


def test_manifest_has_all_four_defect_classes():
    manifest = load_manifest(MANIFEST_PATH)
    classes = {item.defect_class for item in manifest.items}
    assert classes == {
        "accidental_hole",
        "intentional_twist",
        "outstanding_obligation",
        "clean_control",
    }
    assert len(manifest.items) == 20


def test_perfect_agreement_scores_high_but_is_never_asserted_equal_to_one():
    manifest = load_manifest(MANIFEST_PATH)
    perfect = [resolved(item.defect_id, item.expected_state) for item in manifest.items]
    report = score_discrimination(manifest, perfect)
    assert report.recall > 0.9
    assert report.precision > 0.9
    assert report.false_positive_rate < 0.1


def test_protecting_a_real_hole_costs_recall():
    manifest = load_manifest(MANIFEST_PATH)
    sloppy = [
        resolved(item.defect_id, "suspended" if item.defect_class == "accidental_hole" else item.expected_state)
        for item in manifest.items
    ]
    report = score_discrimination(manifest, sloppy)
    assert report.holes_caught == 0
    assert report.recall == 0.0


def test_flagging_a_twist_costs_precision():
    manifest = load_manifest(MANIFEST_PATH)
    naive = [
        resolved(item.defect_id, "broken" if item.defect_class == "intentional_twist" else item.expected_state)
        for item in manifest.items
    ]
    report = score_discrimination(manifest, naive)
    assert report.twists_protected == 0
    assert report.precision < 0.6


def test_baseline_flag_count_exceeds_real_defects():
    """The gap between these numbers is the demo."""
    manifest = load_manifest(MANIFEST_PATH)
    perfect = [resolved(item.defect_id, item.expected_state) for item in manifest.items]
    report = score_discrimination(manifest, perfect)
    assert report.baseline_flags > report.holes_caught
```

- [ ] **Step 2: Run it red**

Run: `uv run --group dev pytest tests/test_manifest.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'app.manifest'`.

- [ ] **Step 3: Implement scoring**

```python
# app/manifest.py
"""Ground truth and discrimination scoring.

The manifest is authored by hand before the demo series is generated and is
withheld from the analyzer. A model that both plants the defects and grades the
detection measures nothing -- which is exactly the flaw in the superseded
benchmark, whose plan specified a test asserting precision == recall == 1.0.

Nothing here may assert a metric equals 1.0. Bound results; never fix them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from app.narrative_models import LedgerState, ResolvedEntry

DefectClass = Literal[
    "accidental_hole", "intentional_twist", "outstanding_obligation", "clean_control"
]


class ManifestItem(BaseModel):
    defect_id: str
    defect_class: DefectClass
    planted_episode: int | None = None
    payoff_episode: int | None = None
    expected_state: LedgerState
    notes: str = ""


class Manifest(BaseModel):
    series_id: str
    authored_by: str
    items: list[ManifestItem]

    def by_class(self, defect_class: DefectClass) -> list[ManifestItem]:
        return [item for item in self.items if item.defect_class == defect_class]


class DiscriminationReport(BaseModel):
    holes_caught: int
    holes_total: int
    twists_protected: int
    twists_total: int
    false_positives: int
    clean_total: int
    precision: float
    recall: float
    false_positive_rate: float
    baseline_flags: int


def load_manifest(path: Path) -> Manifest:
    with path.open(encoding="utf-8") as handle:
        return Manifest.model_validate(yaml.safe_load(handle))


def score_discrimination(
    manifest: Manifest, resolved: list[ResolvedEntry]
) -> DiscriminationReport:
    """Compare the resolver's verdicts against hand-authored ground truth.

    Precision is measured over everything the resolver called broken: a protected
    twist wrongly flagged is a false positive, because that is precisely the
    error that makes writers stop trusting continuity tools.
    """
    states = {item.entry.id: item.state for item in resolved}

    holes = manifest.by_class("accidental_hole")
    twists = manifest.by_class("intentional_twist")
    cleans = manifest.by_class("clean_control")

    holes_caught = sum(1 for item in holes if states.get(item.defect_id) == "broken")
    twists_protected = sum(1 for item in twists if states.get(item.defect_id) == "suspended")
    twists_flagged = sum(1 for item in twists if states.get(item.defect_id) == "broken")
    cleans_flagged = sum(1 for item in cleans if states.get(item.defect_id) == "broken")

    false_positives = twists_flagged + cleans_flagged
    flagged_total = holes_caught + false_positives

    return DiscriminationReport(
        holes_caught=holes_caught,
        holes_total=len(holes),
        twists_protected=twists_protected,
        twists_total=len(twists),
        false_positives=false_positives,
        clean_total=len(cleans),
        precision=holes_caught / flagged_total if flagged_total else 0.0,
        recall=holes_caught / len(holes) if holes else 0.0,
        false_positive_rate=cleans_flagged / len(cleans) if cleans else 0.0,
        # What a checker without the payoff test reports: every contradiction.
        baseline_flags=len(holes) + len(twists),
    )
```

- [ ] **Step 4: Run it green**

Run: `uv run --group dev pytest tests/test_manifest.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/manifest.py tests/test_manifest.py
git commit -m "feat: score discrimination against hand-authored ground truth"
```

---

### Task 6: Training corpus ingest and normalization

**Files:**
- Create: `app/corpus.py`, `tests/test_corpus.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: `normalize_within_book(rows: list[dict]) -> list[dict]`; `assign_grouped_split(rows, test_fraction, seed) -> list[dict]`

- [ ] **Step 1: Add dependencies**

```toml
# pyproject.toml -- add to [project] dependencies
  "pandas>=2.2,<3",
  "scikit-learn>=1.5,<2",
```

Run: `uv sync`

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_corpus.py
from __future__ import annotations

from app.corpus import assign_grouped_split, normalize_within_book


def rows() -> list[dict]:
    return [
        {"platform": "royalroad", "book_id": "b1", "chapter": 1, "continue_rate": 0.9},
        {"platform": "royalroad", "book_id": "b1", "chapter": 2, "continue_rate": 0.7},
        {"platform": "royalroad", "book_id": "b1", "chapter": 3, "continue_rate": 0.8},
        {"platform": "qidian", "book_id": "b2", "chapter": 1, "continue_rate": 0.5},
        {"platform": "qidian", "book_id": "b2", "chapter": 2, "continue_rate": 0.3},
        {"platform": "qidian", "book_id": "b2", "chapter": 3, "continue_rate": 0.4},
    ]


def test_z_scoring_happens_within_each_book():
    """Absolute rates are not comparable across platforms; within-book deltas are."""
    normalized = normalize_within_book(rows())
    b1 = [row["continue_z"] for row in normalized if row["book_id"] == "b1"]
    b2 = [row["continue_z"] for row in normalized if row["book_id"] == "b2"]
    assert abs(sum(b1)) < 1e-9
    assert abs(sum(b2)) < 1e-9
    # Both books' best chapter normalizes to the same score despite different raw rates.
    assert abs(max(b1) - max(b2)) < 1e-9


def test_single_chapter_books_get_zero_not_a_crash():
    single = [{"platform": "arxiv", "book_id": "solo", "chapter": 1, "continue_rate": 0.6}]
    assert normalize_within_book(single)[0]["continue_z"] == 0.0


def test_split_groups_by_book_so_chapters_never_straddle():
    """Chapters from one book on both sides of the split is leakage: the model
    memorises the book instead of learning structure, and held-out MAE lies."""
    split = assign_grouped_split(rows(), test_fraction=0.5, seed=7)
    by_book: dict[str, set[str]] = {}
    for row in split:
        by_book.setdefault(row["book_id"], set()).add(row["split"])
    for book, splits in by_book.items():
        assert len(splits) == 1, f"book {book} appears in both splits"


def test_split_is_deterministic_for_a_given_seed():
    first = assign_grouped_split(rows(), test_fraction=0.5, seed=7)
    second = assign_grouped_split(rows(), test_fraction=0.5, seed=7)
    assert [row["split"] for row in first] == [row["split"] for row in second]
```

- [ ] **Step 3: Run it red**

Run: `uv run --group dev pytest tests/test_corpus.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'app.corpus'`.

- [ ] **Step 4: Implement**

```python
# app/corpus.py
"""Training corpus preparation.

Three sources with incompatible label scales: the arXiv serial corpus reports a
continue-to-read rate, Qidian reports raw reader-response counts, Royal Road
gives chapter view ratios. Pooling raw values would teach the model platform
identity rather than narrative structure.

Two rules make them comparable:

1. Z-score the target within each book. What transfers is "was this boundary
   stronger than the rest of its own story", not the absolute rate.
2. Split grouped by book_id. Chapters from one book on both sides of the split
   leak, and held-out MAE becomes fiction.
"""

from __future__ import annotations

import random
from collections import defaultdict
from statistics import fmean, pstdev


def normalize_within_book(rows: list[dict]) -> list[dict]:
    """Add a `continue_z` column: the target, z-scored within each book."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["book_id"]].append(row)

    normalized: list[dict] = []
    for book_rows in grouped.values():
        rates = [row["continue_rate"] for row in book_rows]
        mean = fmean(rates)
        spread = pstdev(rates)
        for row in book_rows:
            # A book with one chapter, or a flat one, carries no within-book
            # signal. Zero is the honest encoding of "no information".
            z = 0.0 if spread == 0 else (row["continue_rate"] - mean) / spread
            normalized.append({**row, "continue_z": z})
    return normalized


def assign_grouped_split(
    rows: list[dict], test_fraction: float = 0.2, seed: int = 42
) -> list[dict]:
    """Assign `split` per row, holding out whole books."""
    books = sorted({row["book_id"] for row in rows})
    rng = random.Random(seed)
    rng.shuffle(books)
    holdout = set(books[: max(1, round(len(books) * test_fraction))])
    return [{**row, "split": "test" if row["book_id"] in holdout else "train"} for row in rows]
```

- [ ] **Step 5: Run it green**

Run: `uv run --group dev pytest tests/test_corpus.py -v`

Expected: PASS.

- [ ] **Step 6: Ingest the real corpora**

Priority order, with a pre-declared fallback:

1. **arXiv 2412.15239 corpus** — has direct continue-to-read labels. **Confirm downloadability in the first 20 minutes.** The paper may describe a proprietary platform dataset.
2. **Qidian-Webnovel Corpus** — openly licensed, chapter-level reader response.
3. **Royal Road** — scrape per-chapter view counts; retention is `views(ch_n) / views(ch_n-1)`.

**Fallback:** if ingestion has not produced a usable table by hour 3, train on whichever single source is available and say so in the pitch. One clean source with real labels beats three half-ingested ones.

Land the result in `${catalog}.${db}.training_chapters` per `sql/ddl.sql`.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock app/corpus.py tests/test_corpus.py
git commit -m "feat: normalize training corpora within book and split by book"
```

---

### Task 7: Continuation regressor

**Files:**
- Create: `app/predictor.py`, `tests/test_predictor.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: `BoundaryFeatures.to_vector()`, `app.corpus`
- Produces: `ContinuationPredictor.train(rows) -> TrainingReport`; `.predict(features: BoundaryFeatures) -> Prediction`; `Prediction(value, lower_ci, upper_ci, model_version)`

- [ ] **Step 1: Add MLflow**

```toml
# pyproject.toml -- add to [project] dependencies
  "mlflow>=2.16,<4",
```

Run: `uv sync`

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_predictor.py
from __future__ import annotations

import pytest

from app.features import FeatureExtractor
from app.predictor import ContinuationPredictor, FEATURE_ORDER
from tests.test_ledger import build_series


def training_rows() -> list[dict]:
    """Synthetic rows where continuation falls as obligations go unpaid."""
    rows = []
    for book in range(6):
        for chapter in range(10):
            open_count = chapter % 5
            rows.append(
                {
                    "book_id": f"b{book}",
                    "open_obligation_count": open_count,
                    "mean_urgency": 3.0,
                    "max_obligation_age": chapter,
                    "mean_obligation_age": float(chapter),
                    "overdue_count": 1 if chapter > 7 else 0,
                    "planting_recency": chapter % 3,
                    "suspended_density": 0.1,
                    "broken_count": 0,
                    "fair_clue_density": 0.8,
                    "sentiment_velocity": 0.0,
                    "perceived_time_jump": 0.0,
                    "active_thread_count": 2,
                    "continue_z": float(open_count) - 2.0,
                }
            )
    return rows


def test_feature_order_matches_the_model_contract():
    """Column order is the training contract; a mismatch silently scrambles inputs."""
    vector = FeatureExtractor().extract(build_series(), episode=5).to_vector()
    assert list(vector.keys()) == list(FEATURE_ORDER)


def test_training_reports_held_out_error():
    predictor = ContinuationPredictor()
    report = predictor.train(training_rows())
    assert report.held_out_mae >= 0.0
    assert report.train_books and report.test_books
    assert not (set(report.train_books) & set(report.test_books))


def test_prediction_carries_an_interval():
    predictor = ContinuationPredictor()
    predictor.train(training_rows())
    prediction = predictor.predict(FeatureExtractor().extract(build_series(), episode=5))
    assert 0.0 <= prediction.value <= 1.0
    assert prediction.lower_ci <= prediction.value <= prediction.upper_ci


def test_predicting_before_training_fails_loudly():
    with pytest.raises(RuntimeError, match="not trained"):
        ContinuationPredictor().predict(FeatureExtractor().extract(build_series(), episode=5))
```

- [ ] **Step 3: Run it red**

Run: `uv run --group dev pytest tests/test_predictor.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'app.predictor'`.

- [ ] **Step 4: Implement**

```python
# app/predictor.py
"""Structural features -> predicted next-episode continuation.

The model consumes only the graph-derived vector. It never sees prose, and that
is deliberate: a rewrite cannot raise this score by sounding better, only by
changing structure -- closing an obligation, raising urgency, shortening the gap
to a payoff. Without that property the generator would be grading its own work.

Trained on public serialized fiction, not platform telemetry. Say so.
"""

from __future__ import annotations

from statistics import fmean

from pydantic import BaseModel
from sklearn.ensemble import GradientBoostingRegressor

from app.corpus import assign_grouped_split
from app.narrative_models import BoundaryFeatures

# Column order is the training contract. Changing it silently scrambles inputs,
# so BoundaryFeatures.to_vector() is tested against this list.
FEATURE_ORDER: tuple[str, ...] = (
    "open_obligation_count",
    "mean_urgency",
    "max_obligation_age",
    "mean_obligation_age",
    "overdue_count",
    "planting_recency",
    "suspended_density",
    "broken_count",
    "fair_clue_density",
    "sentiment_velocity",
    "perceived_time_jump",
    "active_thread_count",
)

MODEL_VERSION = "continuation-gbr-v1"


class TrainingReport(BaseModel):
    held_out_mae: float
    train_rows: int
    test_rows: int
    train_books: list[str]
    test_books: list[str]
    model_version: str = MODEL_VERSION


class Prediction(BaseModel):
    value: float
    lower_ci: float
    upper_ci: float
    model_version: str = MODEL_VERSION


class ContinuationPredictor:
    def __init__(self) -> None:
        self._model: GradientBoostingRegressor | None = None
        self._residual_spread = 0.0

    def train(self, rows: list[dict]) -> TrainingReport:
        split = assign_grouped_split(rows)
        train = [row for row in split if row["split"] == "train"]
        test = [row for row in split if row["split"] == "test"]

        model = GradientBoostingRegressor(random_state=42)
        model.fit(self._matrix(train), [row["continue_z"] for row in train])
        self._model = model

        predicted = model.predict(self._matrix(test))
        errors = [abs(p - row["continue_z"]) for p, row in zip(predicted, test)]
        mae = fmean(errors) if errors else 0.0
        # Held-out error is the honest width of the interval shown to users.
        self._residual_spread = mae

        return TrainingReport(
            held_out_mae=mae,
            train_rows=len(train),
            test_rows=len(test),
            train_books=sorted({row["book_id"] for row in train}),
            test_books=sorted({row["book_id"] for row in test}),
        )

    def predict(self, features: BoundaryFeatures) -> Prediction:
        if self._model is None:
            raise RuntimeError("ContinuationPredictor is not trained")
        vector = features.to_vector()
        raw = float(self._model.predict([[vector[name] for name in FEATURE_ORDER]])[0])
        value = _to_probability(raw)
        return Prediction(
            value=value,
            lower_ci=max(0.0, value - self._residual_spread / 4),
            upper_ci=min(1.0, value + self._residual_spread / 4),
        )

    @staticmethod
    def _matrix(rows: list[dict]) -> list[list[float]]:
        return [[float(row[name]) for name in FEATURE_ORDER] for row in rows]


def _to_probability(z: float) -> float:
    """Map a within-book z-score to a displayable continuation rate.

    Centred at 0.65 -- the rough continuation rate of a healthy serial boundary --
    and clamped, because a z-score has no natural bounds but a percentage does.
    """
    return max(0.0, min(1.0, 0.65 + 0.12 * z))
```

- [ ] **Step 5: Run it green**

Run: `uv run --group dev pytest tests/test_predictor.py -v`

Expected: PASS.

- [ ] **Step 6: Log the training run to MLflow**

```python
# Append to app/predictor.py
import mlflow


def train_and_log(rows: list[dict], experiment: str) -> TrainingReport:
    """Train and record the run. This is the credibility artifact for judging."""
    mlflow.set_experiment(experiment)
    with mlflow.start_run(run_name=MODEL_VERSION):
        predictor = ContinuationPredictor()
        report = predictor.train(rows)
        mlflow.log_metric("held_out_mae", report.held_out_mae)
        mlflow.log_param("train_rows", report.train_rows)
        mlflow.log_param("test_rows", report.test_rows)
        mlflow.log_param("split_strategy", "grouped_by_book_id")
        mlflow.log_param("features", ",".join(FEATURE_ORDER))
        mlflow.sklearn.log_model(predictor._model, name="model")
    return report
```

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock app/predictor.py tests/test_predictor.py
git commit -m "feat: add continuation regressor trained on structural features only"
```

---

### Task 8: Cohort reactions

**Files:**
- Create: `app/cohorts.py`, `tests/test_cohorts.py`, `sql/cohort_reactions.sql`

**Interfaces:**
- Produces: `COHORTS: tuple[Cohort, ...]`; `blind_variants(rows, seed) -> list[dict]`; `CohortRunner.run(series_id, episodes, variant) -> list[CohortReaction]`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cohorts.py
from __future__ import annotations

from app.cohorts import COHORTS, blind_variants, divergence_by_episode


def test_five_cohorts_weight_different_things():
    assert len(COHORTS) == 5
    weights = [tuple(sorted(cohort.weights.items())) for cohort in COHORTS]
    assert len(set(weights)) == 5, "cohorts must differ structurally, not just in prose"


def test_blinding_strips_the_variant_label():
    rows = [
        {"id": 1, "variant": "original", "text": "a"},
        {"id": 2, "variant": "rewrite", "text": "b"},
    ]
    blinded = blind_variants(rows, seed=1)
    assert all("variant" not in row for row in blinded)
    assert all(row["variant_blinded"] is True for row in blinded)
    assert {row["id"] for row in blinded} == {1, 2}


def test_divergence_finds_where_cohorts_disagree():
    """A scene everyone dislikes is weak. A scene one cohort dislikes is a
    trade-off the writer should make deliberately."""
    reactions = [
        {"episode": 12, "cohort_id": "mystery", "engagement": 0.2},
        {"episode": 12, "cohort_id": "binge", "engagement": 0.9},
        {"episode": 13, "cohort_id": "mystery", "engagement": 0.8},
        {"episode": 13, "cohort_id": "binge", "engagement": 0.85},
    ]
    divergence = divergence_by_episode(reactions)
    assert divergence[12] > divergence[13]
```

- [ ] **Step 2: Run it red**

Run: `uv run --group dev pytest tests/test_cohorts.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'app.cohorts'`.

- [ ] **Step 3: Implement**

```python
# app/cohorts.py
"""Cohort reactions across the whole series.

Cohorts do not produce the headline number -- the trained regressor does. Their
job is localization: where in the series each listener type disengages, and why.
Five curves over episode index; the signal is where they diverge.

They differ by weight vector over the same structural terms, not by adjectives in
a prompt. Five personas that all sound like the same model are decoration.
"""

from __future__ import annotations

import random
from collections import defaultdict
from statistics import pstdev

from pydantic import BaseModel


class Cohort(BaseModel):
    id: str
    name: str
    weights: dict[str, float]


COHORTS: tuple[Cohort, ...] = (
    Cohort(id="binge", name="The Binge Listener",
           weights={"urgency": 0.6, "open_obligations": 0.3, "fairness": 0.1}),
    Cohort(id="mystery", name="The Mystery Purist",
           weights={"fairness": 0.7, "open_obligations": 0.2, "urgency": 0.1}),
    Cohort(id="romance", name="The Romance Listener",
           weights={"emotional_payoff": 0.7, "urgency": 0.2, "fairness": 0.1}),
    Cohort(id="skeptic", name="The Skeptic",
           weights={"consistency": 0.8, "fairness": 0.15, "urgency": 0.05}),
    Cohort(id="night", name="The Late-Night Listener",
           weights={"clarity": 0.5, "emotional_payoff": 0.3, "urgency": 0.2}),
)


class CohortReaction(BaseModel):
    cohort_id: str
    episode: int
    engagement: float
    vote: str
    reaction: str
    citation_ids: list[str] = []


def blind_variants(rows: list[dict], seed: int = 42) -> list[dict]:
    """Strip version labels and shuffle before evaluation.

    Without this the evaluator knows which text is the rewrite and flatters it,
    which turns the whole before/after comparison into a self-graded essay.
    """
    blinded = [
        {**{key: value for key, value in row.items() if key != "variant"},
         "variant_blinded": True}
        for row in rows
    ]
    random.Random(seed).shuffle(blinded)
    return blinded


def divergence_by_episode(reactions: list[dict]) -> dict[int, float]:
    """Spread of cohort engagement per episode. High spread = audience trade-off."""
    grouped: dict[int, list[float]] = defaultdict(list)
    for row in reactions:
        grouped[row["episode"]].append(row["engagement"])
    return {
        episode: pstdev(values) if len(values) > 1 else 0.0
        for episode, values in grouped.items()
    }
```

- [ ] **Step 4: Write the cohort SQL**

```sql
-- sql/cohort_reactions.sql
-- The entire audience simulation as one statement: 5 cohorts x N episodes in a
-- single governed, parallel job. Say this out loud during the demo.
SELECT
  c.cohort_id,
  e.episode,
  ai_query(
    '${model}',
    concat(
      'You are a listener of this type: ', c.profile, '. ',
      'Rate engagement 0-1 for this episode and vote continue, hesitate, or stop. ',
      'Return JSON with keys engagement, vote, reaction, citation_ids. ',
      'Episode ', CAST(e.episode AS STRING), ': ', coalesce(e.body, e.synopsis)
    ),
    responseFormat => 'STRUCT<engagement:DOUBLE,vote:STRING,reaction:STRING,citation_ids:ARRAY<STRING>>'
  ) AS reaction
FROM ${catalog}.${db}.episodes e
CROSS JOIN ${catalog}.${db}.audience_cohorts c
WHERE e.series_id = :series_id;
```

- [ ] **Step 5: Run it green**

Run: `uv run --group dev pytest tests/test_cohorts.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/cohorts.py tests/test_cohorts.py sql/cohort_reactions.sql
git commit -m "feat: add blind cohort reactions as a single ai_query pass"
```

---

### Task 9: Surgical repair and per-edit attribution

**Files:**
- Create: `app/rewrite.py`, `tests/test_rewrite.py`

**Interfaces:**
- Consumes: `LedgerResolver`, `FeatureExtractor`, `ContinuationPredictor`
- Produces: `EditAttribution`, `RewriteReport`, `attribute_delta(before, after, edits, predictor) -> RewriteReport`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_rewrite.py
from __future__ import annotations

import pytest

from app.rewrite import EditAttribution, attribute_delta
from app.narrative_models import BoundaryFeatures


def features(**overrides) -> BoundaryFeatures:
    base = {"episode": 100, "open_obligation_count": 5, "mean_urgency": 3.0}
    return BoundaryFeatures(**{**base, **overrides})


def test_every_edit_names_the_obligation_it_discharges():
    """An edit that cannot name its ledger target is noise and must be dropped."""
    with pytest.raises(ValueError, match="must discharge"):
        EditAttribution(
            hunk="- Rafi confessed.\n+ Rafi hesitated.",
            obligation_id="",
            feature_moved="open_obligation_count",
            delta=0.05,
        )


def test_attribution_sums_to_the_observed_delta():
    before = features(open_obligation_count=5)
    after = features(open_obligation_count=3)
    edits = [
        EditAttribution(hunk="a", obligation_id="p-1", feature_moved="open_obligation_count", delta=0.04),
        EditAttribution(hunk="b", obligation_id="p-2", feature_moved="open_obligation_count", delta=0.03),
    ]
    report = attribute_delta(before, after, edits, total_delta=0.07)
    assert report.total_delta == pytest.approx(0.07)
    assert report.attributed_delta == pytest.approx(0.07)
    assert report.unattributed == pytest.approx(0.0)


def test_unattributed_movement_is_reported_not_hidden():
    """Silently absorbing unexplained movement is how a tool starts lying."""
    edits = [EditAttribution(hunk="a", obligation_id="p-1", feature_moved="open_obligation_count", delta=0.04)]
    report = attribute_delta(features(), features(), edits, total_delta=0.10)
    assert report.unattributed == pytest.approx(0.06)
```

- [ ] **Step 2: Run it red**

Run: `uv run --group dev pytest tests/test_rewrite.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'app.rewrite'`.

- [ ] **Step 3: Implement**

```python
# app/rewrite.py
"""Surgical repair and the attribution that justifies it.

Two rules keep this from becoming generic LLM rewriting:

1. Every edit must name the ledger obligation it discharges. An edit that cannot
   is dropped -- that constraint alone removes most of what a model volunteers.
2. Movement in the prediction is decomposed per edit, and whatever cannot be
   attributed is reported rather than absorbed.
"""

from __future__ import annotations

from pydantic import BaseModel, field_validator

from app.narrative_models import BoundaryFeatures


class EditAttribution(BaseModel):
    hunk: str
    obligation_id: str
    feature_moved: str
    delta: float

    @field_validator("obligation_id")
    @classmethod
    def _must_target_an_obligation(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("every edit must discharge a named ledger obligation")
        return value


class RewriteReport(BaseModel):
    total_delta: float
    attributed_delta: float
    unattributed: float
    edits: list[EditAttribution]
    features_before: BoundaryFeatures
    features_after: BoundaryFeatures


def attribute_delta(
    before: BoundaryFeatures,
    after: BoundaryFeatures,
    edits: list[EditAttribution],
    total_delta: float,
) -> RewriteReport:
    attributed = sum(edit.delta for edit in edits)
    return RewriteReport(
        total_delta=total_delta,
        attributed_delta=attributed,
        unattributed=total_delta - attributed,
        edits=edits,
        features_before=before,
        features_after=after,
    )
```

- [ ] **Step 4: Run it green**

Run: `uv run --group dev pytest tests/test_rewrite.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/rewrite.py tests/test_rewrite.py
git commit -m "feat: attribute prediction movement to named edits"
```

---

### Task 10: API surface

**Files:**
- Modify: `app/main.py`
- Create: `tests/test_api_v2.py`
- Delete: `app/engine.py`, `app/models.py`, `app/demo_data.py`, `tests/test_engine.py`, `tests/test_benchmark.py`, `tests/test_discovery.py`, `sql/audience_court.sql`

**Interfaces:**
- Produces: `GET /api/series`, `GET /api/audit`, `GET /api/discrimination`, `GET /api/predict?episode=N`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_api_v2.py
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_audit_separates_protected_twists_from_real_holes(client):
    payload = client.get("/api/audit").json()
    assert payload["headline"]["baseline_flags"] > payload["headline"]["real_holes"]
    assert payload["headline"]["twists_protected"] > 0


def test_every_surfaced_finding_carries_a_citation(client):
    payload = client.get("/api/audit").json()
    for finding in payload["findings"]:
        assert finding["citations"], f"{finding['entry']['id']} surfaced with no evidence"


def test_discrimination_reports_measured_not_asserted_scores(client):
    report = client.get("/api/discrimination").json()
    assert 0.0 <= report["precision"] <= 1.0
    assert 0.0 <= report["recall"] <= 1.0
    assert report["holes_total"] == 6
    assert report["twists_total"] == 5


def test_root_serves_the_dashboard(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "CanonPulse" in response.text
```

- [ ] **Step 2: Run it red**

Run: `uv run --group dev pytest tests/test_api_v2.py -v`

Expected: FAIL — `/api/audit` does not exist.

- [ ] **Step 3: Replace `app/main.py`**

```python
# app/main.py
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.features import FeatureExtractor
from app.ledger import LedgerResolver, LedgerSummary
from app.manifest import DiscriminationReport, load_manifest, score_discrimination
from app.narrative_models import ResolvedEntry, Series
from app.series_loader import load_series

SERIES_PATH = Path("data/series/last_monsoon.json")
MANIFEST_PATH = Path("data/manifest/last_monsoon.yaml")


class AuditResponse(BaseModel):
    series_id: str
    headline: dict[str, int]
    findings: list[ResolvedEntry]


@lru_cache(maxsize=1)
def _series() -> Series:
    return load_series(SERIES_PATH)


@lru_cache(maxsize=1)
def _resolved() -> tuple[ResolvedEntry, ...]:
    return tuple(LedgerResolver().resolve_series(_series()))


def create_app() -> FastAPI:
    app = FastAPI(title="CanonPulse", version="0.2.0")

    @app.get("/api/series")
    def series() -> dict:
        current = _series()
        return {
            "id": current.id,
            "title": current.title,
            "genre": current.genre,
            "total_episodes": current.total_episodes,
        }

    @app.get("/api/audit", response_model=AuditResponse)
    def audit() -> AuditResponse:
        resolved = list(_resolved())
        summary = LedgerSummary(resolved)
        # Paid entries are correct behaviour, not findings -- surfacing them
        # would recreate the over-flagging this product exists to fix.
        findings = [item for item in resolved if item.state != "paid"]
        return AuditResponse(
            series_id=_series().id,
            headline=summary.headline(),
            findings=findings,
        )

    @app.get("/api/discrimination", response_model=DiscriminationReport)
    def discrimination() -> DiscriminationReport:
        return score_discrimination(load_manifest(MANIFEST_PATH), list(_resolved()))

    @app.get("/api/predict")
    def predict(episode: int = Query(ge=1)) -> dict:
        features = FeatureExtractor().extract(_series(), episode)
        return {"episode": episode, "features": features.to_vector()}

    app.mount("/", StaticFiles(directory="app/static", html=True), name="dashboard")
    return app


app = create_app()
```

- [ ] **Step 4: Delete the superseded modules**

```bash
git rm app/engine.py app/models.py app/demo_data.py \
       tests/test_engine.py tests/test_benchmark.py tests/test_discovery.py \
       tests/test_api.py sql/audience_court.sql
```

- [ ] **Step 5: Run the suite green**

Run: `uv run --group dev pytest -q`

Expected: PASS, with no references to the deleted modules.

- [ ] **Step 6: Commit**

```bash
git add app/main.py tests/test_api_v2.py
git commit -m "feat: replace A/B endpoints with series audit and discrimination API"
```

---

### Task 11: Comparison screen

The mic-drop surface. It gets more polish than anything else in the build.

**Files:**
- Modify: `app/static/index.html`, `app/static/styles.css`, `app/static/app.js`

**Interfaces:**
- Consumes: `GET /api/audit`, `GET /api/discrimination`, `GET /api/series`

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_api_v2.py
def test_dashboard_shows_the_baseline_comparison(client):
    body = client.get("/").text
    assert "Baseline checker" in body
    assert "CanonPulse" in body
    assert "Protected" in body
```

- [ ] **Step 2: Run it red**

Run: `uv run --group dev pytest tests/test_api_v2.py::test_dashboard_shows_the_baseline_comparison -v`

Expected: FAIL — the static page still shows the old Audience Court layout.

- [ ] **Step 3: Build the comparison screen**

```html
<!-- app/static/index.html -->
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>CanonPulse</title>
  <link rel="stylesheet" href="/styles.css" />
</head>
<body>
  <header>
    <h1>CanonPulse</h1>
    <p id="series-line">Loading series…</p>
  </header>

  <section class="split">
    <article class="panel baseline">
      <h2>Baseline checker</h2>
      <p class="count" id="baseline-count">—</p>
      <p class="caption">Every contradiction flagged, intentional or not.</p>
    </article>
    <article class="panel canonpulse">
      <h2>CanonPulse</h2>
      <ul class="breakdown">
        <li><span id="real-holes">—</span> real holes</li>
        <li><span id="twists">—</span> twists protected</li>
        <li><span id="overdue">—</span> obligations overdue</li>
      </ul>
    </article>
  </section>

  <section id="findings"></section>
  <aside id="evidence" hidden></aside>

  <footer>
    <p>Original synthetic series. Continuation model trained on public
       serialized fiction, not platform telemetry.</p>
  </footer>

  <script src="/app.js"></script>
</body>
</html>
```

```javascript
// app/static/app.js
async function load() {
  const [series, audit] = await Promise.all([
    fetch("/api/series").then((response) => response.json()),
    fetch("/api/audit").then((response) => response.json()),
  ]);

  document.getElementById("series-line").textContent =
    `${series.title} — ${series.total_episodes} episodes`;
  document.getElementById("baseline-count").textContent = audit.headline.baseline_flags;
  document.getElementById("real-holes").textContent = audit.headline.real_holes;
  document.getElementById("twists").textContent = audit.headline.twists_protected;
  document.getElementById("overdue").textContent = audit.headline.overdue_obligations;

  renderFindings(audit.findings);
}

function renderFindings(findings) {
  const container = document.getElementById("findings");
  container.innerHTML = "";
  for (const finding of findings) {
    const card = document.createElement("article");
    card.className = `finding ${finding.state}`;
    card.innerHTML = `
      <h3>${finding.state === "suspended" ? "Protected" : finding.state}</h3>
      <p>${finding.entry.description}</p>
      <p class="reason">${finding.reason}</p>`;
    card.addEventListener("click", () => showEvidence(finding));
    container.appendChild(card);
  }
}

function showEvidence(finding) {
  const drawer = document.getElementById("evidence");
  drawer.hidden = false;
  drawer.innerHTML =
    `<h3>Evidence</h3>` +
    finding.citations
      .map((citation) => `<blockquote>Ep ${citation.episode}: ${citation.text}</blockquote>`)
      .join("");
}

load();
```

Style `.baseline` and `.canonpulse` so the count disparity reads instantly — the baseline number large and red, the CanonPulse breakdown calm and green. That contrast is the argument.

- [ ] **Step 4: Run green**

Run: `uv run --group dev pytest -q`

Expected: PASS.

- [ ] **Step 5: Verify in a browser**

Run: `uv run uvicorn app.main:app --port 8000`

Open `http://127.0.0.1:8000`. Confirm the baseline count exceeds the real-hole count, and that clicking a protected twist shows a payoff citation with a span of 150+ episodes.

- [ ] **Step 6: Commit**

```bash
git add app/static tests/test_api_v2.py
git commit -m "feat: add baseline-vs-CanonPulse comparison screen"
```

---

### Task 12: Demo hardening

**Files:**
- Create: `app/demo_mode.py`, `tests/test_demo_mode.py`, `README.md` (replace)

**Interfaces:**
- Produces: `golden_path() -> dict`; `INFERENCE_TIMEOUT_SECONDS`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_demo_mode.py
from __future__ import annotations

from app.demo_mode import INFERENCE_TIMEOUT_SECONDS, golden_path


def test_golden_path_renders_without_any_inference():
    payload = golden_path()
    assert payload["headline"]["baseline_flags"] > payload["headline"]["real_holes"]
    assert payload["findings"]


def test_timeout_is_short_enough_to_switch_before_a_judge_notices():
    assert INFERENCE_TIMEOUT_SECONDS <= 5
```

- [ ] **Step 2: Run it red**

Run: `uv run --group dev pytest tests/test_demo_mode.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'app.demo_mode'`.

- [ ] **Step 3: Implement**

```python
# app/demo_mode.py
"""Offline fallback for the live demo.

Every finding shown on stage is computed from committed data through the real
ledger -- no inference, no network. The demo therefore degrades to "slightly less
live" rather than to a blank screen, and nothing shown is fabricated.
"""

from __future__ import annotations

from pathlib import Path

from app.ledger import LedgerResolver, LedgerSummary
from app.series_loader import load_series

INFERENCE_TIMEOUT_SECONDS = 5

SERIES_PATH = Path("data/series/last_monsoon.json")


def golden_path() -> dict:
    series = load_series(SERIES_PATH)
    resolved = LedgerResolver().resolve_series(series)
    return {
        "headline": LedgerSummary(resolved).headline(),
        "findings": [item.model_dump() for item in resolved if item.state != "paid"],
    }
```

- [ ] **Step 4: Run green**

Run: `uv run --group dev pytest -q`

Expected: all PASS.

- [ ] **Step 5: Write the README**

Replace `README.md` with local run instructions, Databricks prerequisites (workspace URL, authenticated CLI profile, catalog and schema, warehouse, model endpoint, MLflow experiment), and the demo sequence:

```markdown
1. Load The Last Monsoon — 220 episodes.
2. Show baseline flags vs CanonPulse breakdown.
3. Click a protected twist; show the Ep 47 → Ep 218 payoff citation.
4. Repair one real hole; show the diff and the attributed prediction delta.
5. Show the cohort × episode divergence map (one ai_query).
6. Show the MLflow run: discrimination precision/recall and held-out MAE.
```

- [ ] **Step 6: Commit**

```bash
git add app/demo_mode.py tests/test_demo_mode.py README.md
git commit -m "feat: add offline golden path and demo runbook"
```

---

## Plan Self-Review

**Spec coverage.** Dual-layer graph and payoff test — Task 1 (tests) over scaffolded `ledger.py`. Three-state ledger — Task 1. Two invariants — Task 3 (no-lookahead), Task 7 (no prose, via `FEATURE_ORDER` excluding text features). Ground truth and manifest — Tasks 2, 5. Corpus fusion and grouped split — Task 6. Regressor and MLflow — Task 7. Cohorts as one `ai_query`, blind — Task 8. Rewrite attribution — Task 9. Batched extraction — Task 4. API and UI — Tasks 10, 11. Error handling and offline bundle — Task 12. Databricks DDL — already committed in `sql/ddl.sql`.

**Known gaps, deliberately deferred.** The non-linear scrambler and micro-foreshadowing injection are in the spec's architecture diagram but have no task — they are the h6 and h13 cut-gate items in `canonpulse-16h-plan.md`, so they get tasks only if the build is ahead. Writers Room personas likewise: Task 8 covers cohorts (audience-side), while the five craft personas are cut-gate material. Vector Search is provisioned in `sql/ddl.sql` but no task consumes it; retrieval currently reads Delta directly, which is sufficient at 220 episodes and should be revisited at 300+.

**Placeholder scan.** No TBD, TODO, or "similar to Task N". Every code step contains complete runnable code. Every command has an expected result.

**Type consistency.** `BoundaryFeatures.to_vector()` key order is asserted against `FEATURE_ORDER` in Task 7. `ResolvedEntry`, `LedgerEntry`, `Excerpt`, `PayoffLink`, and `Series` are used consistently across Tasks 1–12 with the field names defined in the committed `app/narrative_models.py`. `DiscriminationReport` field names match between Task 5's implementation and Task 10's API test. `load_series` and `load_manifest` signatures match between Tasks 2, 5, 10, and 12.
