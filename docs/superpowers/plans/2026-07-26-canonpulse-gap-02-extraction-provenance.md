# Gap 2 — Extraction Provenance and Production Metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every extracted graph row traceable to a source version, extraction run, model configuration, confidence, latency, and retry outcome.

**Architecture:** Adapters continue producing domain objects, but a single provenance envelope wraps every extraction result before graph insertion. The envelope records source hash, episode span, run identifier, model mode, prompt version, validation result, and failure details; citations are rebound to the immutable source version rather than inferred from mutable UI state.

**Tech Stack:** Python 3.11–3.14, Pydantic, FastAPI, pytest, Databricks `ai_query`, Delta/Databricks SQL, MLflow metadata.

## Global Constraints

- Use Python 3.11–3.14 and `uv`.
- All extraction outputs must remain structured graph data; extraction must not generate predictor prose.
- Runtime inference must use governed Databricks Foundation Model APIs; local heuristic extraction remains the deterministic offline test adapter.
- Every citation must identify series, version, episode, and source span.
- Tests cannot require network access or real credentials.
- Retry behavior must preserve failed-row diagnostics and avoid duplicating successful rows.

---

## File map

- Create `app/extraction_models.py`: metadata, failure, citation, and result models.
- Modify `app/extraction.py`, `app/heuristic_extractor.py`, and `app/llm_extractor.py`: normalize adapter outputs.
- Modify `app/ledger.py`: require provenance-bearing citations when inserting graph claims.
- Modify `sql/ddl.sql` and `sql/extract_graph.sql`: extraction-run and row-audit tables.
- Create `scripts/run_extraction_batch.py`: Databricks batch invocation.
- Modify `tests/test_extraction.py`, `tests/test_llm_extractor.py`, and create `tests/test_extraction_provenance.py`.

## Task 1: Define the provenance envelope and citation contract

**Files:**
- Create: `app/extraction_models.py`
- Test: `tests/test_extraction_provenance.py`

**Interfaces:**
- Produces `ExtractionRunMetadata(run_id, source_hash, version_id, model_name, prompt_version, started_at, finished_at, latency_ms, attempt)`.
- Produces `SourceCitation(series_id, version_id, episode_number, start_offset, end_offset, quote_hash)`.
- Produces `ExtractionResult[GraphItem](items, citations, metadata, failures)`.

- [ ] **Step 1: Write the failing test**

```python
def test_citation_rejects_span_from_another_version():
    with pytest.raises(ValueError, match="version_id"):
        SourceCitation(series_id="s", version_id="v2", episode_number=1,
                       start_offset=0, end_offset=4, quote_hash="v1:abc")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_extraction_provenance.py -v`

Expected: FAIL because provenance models and quote-hash validation are absent.

- [ ] **Step 3: Write minimal implementation**

Implement the models with `quote_hash = sha256(f"{version_id}:{source_text[start:end]}")`; reject non-positive spans, missing version identifiers, and metadata with `finished_at < started_at`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_extraction_provenance.py -v`

Expected: PASS for valid citations, invalid spans, and immutable version binding.

- [ ] **Step 5: Commit**

```bash
git add app/extraction_models.py tests/test_extraction_provenance.py
git commit -m "feat: define extraction provenance contracts"
```

## Task 2: Normalize heuristic and LLM adapters

**Files:**
- Modify: `app/extraction.py`
- Modify: `app/heuristic_extractor.py`
- Modify: `app/llm_extractor.py`
- Test: `tests/test_extraction.py`, `tests/test_llm_extractor.py`

**Interfaces:**
- `Extractor.extract_episode(episode: EpisodeInput, context: ExtractionContext) -> ExtractionResult[GraphItem]`.
- `ExtractionContext` contains `series_id`, `version_id`, `source_hash`, `model_name`, and `prompt_version`.

- [ ] **Step 1: Write the failing test**

```python
def test_heuristic_and_llm_adapters_return_identical_metadata_shape():
    context = ExtractionContext(series_id="s", version_id="v1", source_hash="h",
                                model_name="offline", prompt_version="p1")
    result = HeuristicExtractor().extract_episode(sample_episode(), context)
    assert result.metadata.version_id == "v1"
    assert all(c.version_id == "v1" for c in result.citations)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_extraction.py tests/test_llm_extractor.py -k metadata -v`

Expected: FAIL because adapters currently return unwrapped graph objects or unbound citations.

- [ ] **Step 3: Write minimal implementation**

Wrap each adapter response in `ExtractionResult`; capture monotonic latency, increment `attempt`, map parser failures to `ExtractionFailure(code, message, retryable)`, and derive citation quote hashes from the supplied episode text.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_extraction.py tests/test_llm_extractor.py -v`

Expected: PASS with the same typed envelope for offline and governed adapters.

- [ ] **Step 5: Commit**

```bash
git add app/extraction.py app/heuristic_extractor.py app/llm_extractor.py tests/test_extraction.py tests/test_llm_extractor.py
git commit -m "feat: normalize extraction adapter provenance"
```

## Task 3: Persist extraction runs, row outcomes, and retry policy

**Files:**
- Modify: `sql/ddl.sql`
- Modify: `sql/extract_graph.sql`
- Modify: `app/extraction.py`
- Test: `tests/test_extraction_provenance.py`

**Interfaces:**
- Produces `ExtractionRunRepository.start(metadata: ExtractionRunMetadata) -> None`.
- Produces `record_result(result: ExtractionResult[GraphItem]) -> None`.
- Produces `retryable_failures(run_id: str) -> list[ExtractionFailure]`.

- [ ] **Step 1: Write the failing test**

```python
def test_retryable_failures_exclude_permanent_validation_errors():
    repository = InMemoryExtractionRunRepository()
    repository.record_result(result_with_failures(
        ExtractionFailure(code="timeout", message="slow", retryable=True),
        ExtractionFailure(code="schema", message="bad", retryable=False),
    ))
    assert [item.code for item in repository.retryable_failures("run-1")] == ["timeout"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_extraction_provenance.py -k retryable -v`

Expected: FAIL because extraction-run persistence and failure classification are not present.

- [ ] **Step 3: Write minimal implementation**

Add `canonpulse_extraction_run` and `canonpulse_extraction_row` tables keyed by `(run_id, episode_number)`; make result recording upsert by key, and classify timeout/rate-limit/service-unavailable as retryable while schema/citation/contract errors are permanent.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_extraction_provenance.py -k 'retryable or idempotent' -v`

Expected: PASS with one row audit record per episode and no duplicate successful graph items.

- [ ] **Step 5: Commit**

```bash
git add sql/ddl.sql sql/extract_graph.sql app/extraction.py tests/test_extraction_provenance.py
git commit -m "feat: persist extraction run audits"
```

## Task 4: Enforce provenance at graph insertion and wire batch extraction

**Files:**
- Modify: `app/ledger.py`
- Create: `scripts/run_extraction_batch.py`
- Test: `tests/test_extraction_provenance.py`

**Interfaces:**
- `Ledger.add_extraction(result: ExtractionResult[GraphItem]) -> None` rejects unbound citations.
- Batch script consumes `--run-id`, `--version-id`, and `--table` and writes one result per Delta row.

- [ ] **Step 1: Write the failing test**

```python
def test_ledger_rejects_graph_item_without_source_citation():
    ledger = Ledger()
    with pytest.raises(ValueError, match="citation"):
        ledger.add_extraction(ExtractionResult(items=[sample_graph_item()], citations=[],
                                               metadata=sample_metadata(), failures=[]))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_extraction_provenance.py -k ledger -v`

Expected: FAIL because the ledger accepts untraceable graph items.

- [ ] **Step 3: Write minimal implementation**

Require every item to reference at least one citation with matching series/version/episode; have the batch script call one `ai_query` projection over the episode Delta relation, validate each structured response, persist run metadata, and upsert only valid rows.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_extraction_provenance.py tests/test_extraction.py -v`

Expected: PASS with rejected untraceable items and deterministic row-level failure records.

- [ ] **Step 5: Commit**

```bash
git add app/ledger.py scripts/run_extraction_batch.py tests/test_extraction_provenance.py
git commit -m "feat: enforce traceable graph extraction"
```

## Self-review

- Spec coverage: uniform metadata, source hashes, run IDs, latency, confidence-bearing failures, retries, immutable citations, Delta persistence, and batch `ai_query` wiring are covered by Tasks 1–4.
- Completeness scan: the plan contains no unfinished marker or vague implementation instruction.
- Type consistency: adapters return `ExtractionResult[GraphItem]`, metadata uses `ExtractionContext`, and ledger/batch consumers require the same result envelope.
- Verification: run `uv run --group dev pytest tests/test_extraction.py tests/test_llm_extractor.py tests/test_extraction_provenance.py -v`.
