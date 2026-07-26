# Gap 5 — Cohort Reactions and Governed Retrieval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make cohort reactions, vector retrieval, and discovery use reproducible Databricks-backed data with explicit language, version, permission, and citation filters.

**Architecture:** Cohort jobs produce blind, synthetic reaction rows from the same feature boundary and store the prompt/model/version metadata. Retrieval is behind a provider interface with a local deterministic adapter for tests and a Databricks Vector Search adapter for deployment. Discovery applies filters before ranking and returns obligation citations for every result.

**Tech Stack:** Python 3.11–3.14, Pydantic, FastAPI, pytest, Databricks SQL, Vector Search, MLflow metadata.

## Global Constraints

- Cohort reactions and demo metrics are synthetic and must be labeled as such.
- No network or real credentials in unit tests.
- Blind cohort evaluation strips variant labels and randomizes presentation with a recorded seed.
- Retrieval must preserve source version, language, and permission boundaries.
- The product vocabulary is episodes, series, writers, showrunners, listeners, and readers.

---

## File map

- Create `app/retrieval_models.py`: query, result, filter, citation, and cohort contracts.
- Modify `app/cohorts.py`: reproducible cohort generation and blind evaluation.
- Modify `app/discovery.py`: filtered retrieval and explanation citations.
- Create `app/retrieval.py`: local and Vector Search provider implementations.
- Modify `sql/cohort_reactions.sql` and `sql/ddl.sql`: reaction and index-source tables.
- Create `scripts/build_vector_index.py`: Databricks Vector Search sync entry point.
- Modify `tests/test_cohorts.py`, `tests/test_discovery.py`, and create `tests/test_retrieval.py`.

## Task 1: Define cohort and retrieval contracts

**Files:**
- Create: `app/retrieval_models.py`
- Test: `tests/test_retrieval.py`

**Interfaces:**
- Produces `CohortRequest(series_id, version_id, boundaries, personas, seed)`.
- Produces `ReactionRow(cohort_id, boundary, persona_id, variant_id, score, prompt_version, synthetic=True)`.
- Produces `RetrievalQuery(text, series_id, version_id, language, allowed_source_ids, limit)`.
- Produces `RetrievalHit(source_id, score, text, citation: SourceCitation, language)`.

- [ ] **Step 1: Write the failing test**

```python
def test_reaction_row_requires_synthetic_disclosure():
    with pytest.raises(ValueError, match="synthetic"):
        ReactionRow(cohort_id="c", boundary=1, persona_id="p", variant_id="v",
                    score=0.4, prompt_version="p1", synthetic=False)

def test_retrieval_query_requires_version_and_language():
    with pytest.raises(ValueError, match="version_id"):
        RetrievalQuery(text="storm", series_id="s", version_id="", language="en",
                       allowed_source_ids=(), limit=5)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_retrieval.py -v`

Expected: FAIL because contracts do not enforce provenance and synthetic disclosure.

- [ ] **Step 3: Write minimal implementation**

Define Pydantic models with non-empty series/version/language fields, positive limits capped at 50, and a literal `synthetic: Literal[True]` field on `ReactionRow`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_retrieval.py -v`

Expected: PASS for valid contracts and all required-field rejection cases.

- [ ] **Step 5: Commit**

```bash
git add app/retrieval_models.py tests/test_retrieval.py
git commit -m "feat: define governed cohort and retrieval contracts"
```

## Task 2: Implement reproducible blind cohort generation

**Files:**
- Modify: `app/cohorts.py`
- Modify: `sql/cohort_reactions.sql`
- Test: `tests/test_cohorts.py`

**Interfaces:**
- `CohortRunner.generate(request: CohortRequest) -> list[ReactionRow]`.
- `BlindEvaluator.evaluate(rows: Sequence[ReactionRow]) -> CohortEvaluation`.
- `CohortEvaluation` contains seed, model/prompt versions, aggregate scores, and per-boundary results.

- [ ] **Step 1: Write the failing test**

```python
def test_blind_evaluator_is_reproducible_and_strips_variant_labels():
    rows = CohortRunner(stub_model()).generate(sample_cohort_request())
    first = BlindEvaluator(seed=11).evaluate(rows)
    second = BlindEvaluator(seed=11).evaluate(rows)
    assert first == second
    assert first.presented_variant_ids != first.original_variant_ids
    assert first.synthetic is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_cohorts.py -k blind -v`

Expected: FAIL because the current cohort path uses a local summary and does not persist blind-order metadata.

- [ ] **Step 3: Write minimal implementation**

Generate one row per persona × boundary × variant, use the request seed for stable shuffling, remove labels from the model input, store the seed and prompt/model version, and insert rows through the SQL schema keyed by `(cohort_id, boundary, persona_id, variant_id)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_cohorts.py -v`

Expected: PASS for reproducibility, variant-label blindness, synthetic labeling, and duplicate-key rejection.

- [ ] **Step 5: Commit**

```bash
git add app/cohorts.py sql/cohort_reactions.sql tests/test_cohorts.py
git commit -m "feat: make cohort evaluation reproducible"
```

## Task 3: Add retrieval providers and permission-aware filtering

**Files:**
- Create: `app/retrieval.py`
- Modify: `app/discovery.py`
- Test: `tests/test_retrieval.py`, `tests/test_discovery.py`

**Interfaces:**
- `Retriever.search(query: RetrievalQuery) -> list[RetrievalHit]`.
- `LocalRetriever.search` ranks lexical matches deterministically.
- `DatabricksVectorSearchRetriever.search` sends the same filters to the configured Vector Search index.

- [ ] **Step 1: Write the failing test**

```python
def test_retrieval_filters_language_version_and_permissions():
    retriever = LocalRetriever([hit("a", "en", "v1", permitted=True),
                               hit("b", "hi", "v1", permitted=True),
                               hit("c", "en", "v2", permitted=True),
                               hit("d", "en", "v1", permitted=False)])
    result = retriever.search(RetrievalQuery(text="storm", series_id="s", version_id="v1",
                                             language="en", allowed_source_ids=("a",), limit=5))
    assert [item.source_id for item in result] == ["a"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_retrieval.py tests/test_discovery.py -k filters -v`

Expected: FAIL because discovery currently falls back to unconstrained lexical search.

- [ ] **Step 3: Write minimal implementation**

Apply series/version/language/source-ID filters before ranking; make permission an explicit provider predicate; map Vector Search response metadata into `RetrievalHit`; never return a hit without a `SourceCitation`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_retrieval.py tests/test_discovery.py -v`

Expected: PASS for local ranking, filter exclusion, citation binding, and provider parity.

- [ ] **Step 5: Commit**

```bash
git add app/retrieval.py app/discovery.py tests/test_retrieval.py tests/test_discovery.py
git commit -m "feat: add permission-aware retrieval providers"
```

## Task 4: Provision the live Vector Search index and cite discovery explanations

**Files:**
- Create: `scripts/build_vector_index.py`
- Modify: `sql/ddl.sql`, `app/main.py`, `app/discovery.py`
- Test: `tests/test_discovery.py`

**Interfaces:**
- `POST /api/v2/discovery/search` accepts `RetrievalQuery` and returns `list[DiscoveryResult]`.
- `DiscoveryResult` contains `title`, `reason_codes`, `hits`, and `obligation_ids`.
- Script consumes `--source-table`, `--index-name`, and `--endpoint-name` and is safe to rerun.

- [ ] **Step 1: Write the failing test**

```python
def test_discovery_result_explains_each_hit_with_obligation_id(client):
    response = client.post("/api/v2/discovery/search", json=valid_query())
    assert response.status_code == 200
    assert all(item["obligation_ids"] for item in response.json())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_discovery.py -k explanation -v`

Expected: FAIL because the endpoint returns lexical matches without obligation-linked explanation fields.

- [ ] **Step 3: Write minimal implementation**

Create the index source view with source/version/language/permission columns, upsert it through the Databricks Vector Search SDK, configure the provider, and map every returned hit through the ledger obligation index before serializing the response.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_discovery.py tests/test_retrieval.py -v`

Expected: PASS offline; the deployment smoke command must report index endpoint and row-count metadata when credentials are available.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_vector_index.py sql/ddl.sql app/main.py app/discovery.py tests/test_discovery.py
git commit -m "feat: wire cited discovery to vector search"
```

## Self-review

- Spec coverage: Databricks cohort SQL, blind randomization, synthetic disclosure, live/local retrieval parity, language/version/permission filters, vector index sync, and obligation explanations are covered by Tasks 1–4.
- Completeness scan: the plan contains no unfinished marker or vague implementation instruction.
- Type consistency: `RetrievalQuery` feeds both providers; providers return `RetrievalHit`; discovery returns citation-bearing `DiscoveryResult`.
- Verification: run `uv run --group dev pytest tests/test_cohorts.py tests/test_retrieval.py tests/test_discovery.py -v`.
