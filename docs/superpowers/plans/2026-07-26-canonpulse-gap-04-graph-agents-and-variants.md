# Gap 4 — Graph Repair, Scrambling, and Writers Room Agents Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade graph variants from summary edits and generic permutations into constraint-checked node repair, information-order scrambling, and bounded structured agent annotations.

**Architecture:** `G_true` remains immutable chronological reality; all audience-order experiments operate on a copied `G_perceived`. Repair proposals identify an exact corrupted node and preserve unaffected graph content. Scrambler operations are typed and validated against invariants. Writers Room personas return JSON annotations through a bounded runner with timeout, budget, and disagreement capture.

**Tech Stack:** Python 3.11–3.14, NetworkX/domain graph types, Pydantic, FastAPI, pytest, Databricks Foundation Model APIs.

## Global Constraints

- Keep `G_true` invariant across scrambles and repairs unless a deliberate source-version repair is accepted.
- Agents return structured graph annotations, not narrative prose.
- No predictor lookahead and no unverified payoff protection.
- Offline tests use deterministic stubs; no network or real credentials.
- Every variant records parent version, operation, changed node IDs, and validation result.

---

## File map

- Create `app/variant_models.py`: typed operations, proposals, annotations, and validation results.
- Modify `app/variants.py` and `app/rewrite.py`: node-local repair and attribution.
- Modify `app/scrambler.py`: typed information-order operations and invariants.
- Modify `app/personas.py` and `app/foreshadowing.py`: bounded agent runner and structured annotations.
- Modify `app/main.py`: variant and Writers Room endpoints.
- Create `tests/test_variant_models.py`; modify `tests/test_variants.py`, `tests/test_rewrite.py`, `tests/test_foreshadowing.py`, and `tests/test_personas.py`.

## Task 1: Define variant operations and graph invariants

**Files:**
- Create: `app/variant_models.py`
- Test: `tests/test_variant_models.py`

**Interfaces:**
- Produces `VariantOperation(kind: Literal["repair", "swap_order", "hide_clue", "reveal_clue"], node_ids: tuple[str, ...], seed: int)`.
- Produces `Variant(parent_version_id: str, operation: VariantOperation, graph: NarrativeGraph, changed_node_ids: tuple[str, ...])`.
- Produces `validate_variant(original: NarrativeGraph, variant: Variant) -> ValidationResult`.

- [ ] **Step 1: Write the failing test**

```python
def test_variant_validation_rejects_changed_true_graph():
    variant = make_variant(graph=graph_with_changed_true_layer())
    result = validate_variant(original_graph(), variant)
    assert result.valid is False
    assert result.errors == ["G_true nodes or edges changed"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_variant_models.py -v`

Expected: FAIL because operations and invariant validation are not centralized.

- [ ] **Step 3: Write minimal implementation**

Define literal operation kinds, require non-empty node IDs and non-negative seeds, compare `G_true` node/edge hashes before and after, and return all validation errors in stable order.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_variant_models.py -v`

Expected: PASS for unchanged true layer, changed perceived layer, invalid operation, and parent-version checks.

- [ ] **Step 5: Commit**

```bash
git add app/variant_models.py tests/test_variant_models.py
git commit -m "feat: define graph variant invariants"
```

## Task 2: Implement surgical node repair

**Files:**
- Modify: `app/variants.py`, `app/rewrite.py`
- Test: `tests/test_variants.py`, `tests/test_rewrite.py`

**Interfaces:**
- `RepairEngine.propose(graph: NarrativeGraph, issue_id: str) -> RepairProposal`.
- `RepairEngine.apply(graph: NarrativeGraph, proposal: RepairProposal) -> Variant`.
- `RepairProposal` includes `issue_id`, `target_node_id`, `replacement_claim`, `preserved_node_ids`, and `reason_codes`.

- [ ] **Step 1: Write the failing test**

```python
def test_repair_changes_only_target_node_and_records_diff():
    original = graph_with_broken_claim()
    proposal = RepairEngine().propose(original, "issue-1")
    variant = RepairEngine().apply(original, proposal)
    assert variant.changed_node_ids == (proposal.target_node_id,)
    assert unchanged_node_ids(original, variant.graph) == proposal.preserved_node_ids
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_variants.py tests/test_rewrite.py -k repair -v`

Expected: FAIL because repair currently emits a summary-level edit rather than a node-scoped graph diff.

- [ ] **Step 3: Write minimal implementation**

Resolve the issue citation to one claim node, clone only the affected node and incident repair edge, preserve all other node/edge IDs, and reject a proposal whose target is absent or whose replacement changes payoff evidence.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_variants.py tests/test_rewrite.py -v`

Expected: PASS for contradiction repair, missing-target rejection, unchanged citation set outside target, and feature-level attribution.

- [ ] **Step 5: Commit**

```bash
git add app/variants.py app/rewrite.py tests/test_variants.py tests/test_rewrite.py
git commit -m "feat: add surgical graph node repair"
```

## Task 3: Implement all typed information-order scramble operations

**Files:**
- Modify: `app/scrambler.py`
- Test: `tests/test_variants.py`

**Interfaces:**
- `scramble_perceived(graph: NarrativeGraph, operation: VariantOperation) -> Variant`.
- Supported operations are `swap_order`, `hide_clue`, and `reveal_clue`; each updates only `G_perceived` and emits changed node IDs.

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.parametrize("kind", ["swap_order", "hide_clue", "reveal_clue"])
def test_scramble_preserves_true_graph_for_each_operation(kind):
    original = graph_with_clues()
    variant = scramble_perceived(original, VariantOperation(kind=kind, node_ids=("n1", "n2"), seed=3))
    assert graph_hash(variant.graph.g_true) == graph_hash(original.g_true)
    assert variant.operation.kind == kind
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_variants.py -k scramble -v`

Expected: FAIL because current scrambling is a generic permutation without typed constraints.

- [ ] **Step 3: Write minimal implementation**

Implement swap only when both nodes are in `G_perceived`, hide by removing audience-visible clue edges while retaining true edges, reveal by inserting a permitted clue edge, and reject operations that introduce cycles forbidden by the graph contract or alter `G_true`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_variants.py -v`

Expected: PASS for deterministic seeds, invalid node IDs, invariant preservation, and operation-specific edge counts.

- [ ] **Step 5: Commit**

```bash
git add app/scrambler.py tests/test_variants.py
git commit -m "feat: constrain perceived-order graph scrambles"
```

## Task 4: Add bounded structured Writers Room and foreshadowing agents

**Files:**
- Modify: `app/personas.py`, `app/foreshadowing.py`, `app/main.py`
- Test: `tests/test_personas.py`, `tests/test_foreshadowing.py`

**Interfaces:**
- `AgentRunner.run(persona: Persona, graph: NarrativeGraph, budget: int, timeout_s: float) -> AgentAnnotation`.
- `AgentAnnotation` contains `persona_id`, `issue_ids`, `confidence`, `reason_codes`, `latency_ms`, and `timed_out`.
- `run_writers_room(graph: NarrativeGraph, personas: Sequence[Persona]) -> WritersRoomResult` records disagreements without selecting a prose winner.

- [ ] **Step 1: Write the failing test**

```python
def test_writers_room_records_timeout_and_disagreement():
    result = run_writers_room(graph_with_issue(), [slow_persona(), disagreeing_persona()])
    assert result.timeouts == ["slow"]
    assert result.disagreements[0].issue_id == "issue-1"
    assert all(annotation.reason_codes for annotation in result.annotations)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_personas.py tests/test_foreshadowing.py -k 'timeout or disagreement' -v`

Expected: FAIL because agents currently return unconstrained summaries without budget or disagreement records.

- [ ] **Step 3: Write minimal implementation**

Bound each invocation by token budget and wall-clock timeout, parse only the JSON schema, mark malformed responses as failed annotations, retain every persona’s issue classification, and let the ledger verifier—not majority vote—decide graph state.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_personas.py tests/test_foreshadowing.py -v`

Expected: PASS for five persona annotations, timeout capture, malformed-response handling, and deterministic offline stubs.

- [ ] **Step 5: Commit**

```bash
git add app/personas.py app/foreshadowing.py app/main.py tests/test_personas.py tests/test_foreshadowing.py
git commit -m "feat: add bounded structured graph agents"
```

## Self-review

- Spec coverage: node-local repair, full typed scrambler operations, true/perceived invariants, persona timeouts, budgets, structured annotations, and disagreement capture are covered by Tasks 1–4.
- Completeness scan: the plan contains no unfinished marker or vague implementation instruction.
- Type consistency: `VariantOperation` feeds `scramble_perceived`; `Variant` is validated centrally; `AgentAnnotation` and `WritersRoomResult` are JSON-safe API outputs.
- Verification: run `uv run --group dev pytest tests/test_variant_models.py tests/test_variants.py tests/test_rewrite.py tests/test_personas.py tests/test_foreshadowing.py -v`.
