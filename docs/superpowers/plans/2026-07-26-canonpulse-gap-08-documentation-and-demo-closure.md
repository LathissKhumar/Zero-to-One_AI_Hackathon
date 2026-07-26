# Gap 8 — Documentation, Runbook, and Demo Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the repository documentation, plan status, deployment instructions, synthetic-data disclosures, and six-run rehearsal evidence match the implemented product.

**Architecture:** Treat documentation as a tested product contract. A runbook defines prerequisites, local mode, governed Databricks mode, fallback behavior, and the golden path. A rehearsal script writes redacted evidence with commit, deployment, model, feature-schema, and timing identifiers; docs are updated only from observed outputs.

**Tech Stack:** Markdown, Python, pytest, Databricks CLI, MLflow metadata, existing FastAPI/Databricks App.

## Global Constraints

- Never commit `.env`, tokens, generated `mlruns/`, or secret-bearing URLs.
- Preserve explicit disclosure that predictions and cohort reactions are synthetic, not real reader behavior.
- Do not claim live Databricks resources, model versions, or performance numbers without a recorded command output.
- Use Python 3.11–3.14 and `uv`.
- Documentation changes use concise Conventional-Commit-style messages.

---

## File map

- Modify `README.md`: current setup, surfaces, disclosure, and live/local instructions.
- Modify `docs/PRODUCT.md`, `sessionhandoff.md`, and `canonpulse-16h-plan.md`: implementation status and handoff truth.
- Create `docs/superpowers/demo-runbook.md`: exact rehearsal procedure and fallback gate.
- Create `scripts/rehearse_demo.py`: redacted evidence collector with six-run validation.
- Create `tests/test_docs_contract.py`: status/disclosure/link checks.

## Task 1: Establish the documentation contract and status source

**Files:**
- Create: `tests/test_docs_contract.py`
- Modify: `README.md`, `docs/PRODUCT.md`, `sessionhandoff.md`

**Interfaces:**
- Documentation contract requires setup commands, local URL, synthetic disclosure, plan link, and current status text in each named document.
- `extract_status_markers(path: Path) -> set[str]` is used only by tests to detect stale claims.

- [ ] **Step 1: Write the failing test**

```python
def test_docs_disclose_synthetic_metrics_and_current_execution_commands():
    for path in (Path("README.md"), Path("docs/PRODUCT.md"), Path("sessionhandoff.md")):
        text = path.read_text()
        assert "synthetic" in text.lower()
        assert "uv run --group dev pytest" in text
        assert "canonpulse-16h-plan.md" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_docs_contract.py -v`

Expected: FAIL because at least one document still describes the old cohort/retrieval or demo-only state.

- [ ] **Step 3: Write minimal implementation**

Update each document from the current code and deployment evidence; mark each of the eight gap plans as planned or completed only when its tests and smoke output exist; include the exact local test and launch commands plus the synthetic disclosure.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_docs_contract.py -v`

Expected: PASS with no stale “not served” or “missing” statement for a feature already verified.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/PRODUCT.md sessionhandoff.md tests/test_docs_contract.py
git commit -m "docs: align product status and disclosure"
```

## Task 2: Write the reproducible local and Databricks demo runbook

**Files:**
- Create: `docs/superpowers/demo-runbook.md`
- Test: `tests/test_docs_contract.py`

**Interfaces:**
- Runbook sections are `Prerequisites`, `Local Offline Demo`, `Governed Databricks Demo`, `Fallback Gate`, `Evidence Capture`, and `Rehearsal Checklist`.
- Commands include `uv sync`, `uv run --group dev pytest`, `uv run uvicorn app.main:app --port 8000`, and the smoke script flags.

- [ ] **Step 1: Write the failing test**

```python
def test_runbook_contains_safe_fallback_and_rehearsal_count():
    text = Path("docs/superpowers/demo-runbook.md").read_text()
    assert "zero live inference" in text.lower()
    assert "six" in text.lower()
    assert "synthetic" in text.lower()
    assert "--base-url" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_docs_contract.py -k runbook -v`

Expected: FAIL because no verified runbook exists.

- [ ] **Step 3: Write minimal implementation**

Document the golden path from series load through evidence, specify the h14 fallback condition as a measured latency/dependency failure, require precomputed cached reads for fallback, and state that demo metrics are synthetic.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_docs_contract.py -k runbook -v`

Expected: PASS with all required commands, labels, and fallback rules present.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/demo-runbook.md tests/test_docs_contract.py
git commit -m "docs: add reproducible demo runbook"
```

## Task 3: Collect redacted rehearsal evidence and enforce six runs

**Files:**
- Create: `scripts/rehearse_demo.py`
- Modify: `tests/test_docs_contract.py`
- Create: `docs/superpowers/evidence/.gitkeep`

**Interfaces:**
- `run_rehearsal(base_url: str, series_id: str, version_id: str, runs: int = 6) -> RehearsalReport`.
- `RehearsalReport` stores run number, commit SHA, deployment identifier, elapsed milliseconds, endpoint statuses, and failure codes; it excludes headers, tokens, source text, and raw URLs containing credentials.

- [ ] **Step 1: Write the failing test**

```python
def test_rehearsal_report_requires_six_successful_runs():
    report = run_rehearsal_with_fixture(successful_runs=5)
    assert report.exit_code == 1
    assert "six successful runs" in report.failures[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_docs_contract.py -k rehearsal -v`

Expected: FAIL because the report contract and run-count enforcement are absent.

- [ ] **Step 3: Write minimal implementation**

Call the health and golden-path endpoints six times, record only redacted identifiers and timing, fail if any run lacks citations/model/schema linkage or exceeds the runbook threshold, and write JSON evidence under `docs/superpowers/evidence/` only when the caller explicitly supplies an output path.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_docs_contract.py -k rehearsal -v`

Expected: PASS for six successful fixture runs, five-run failure, redaction, and latency failure.

- [ ] **Step 5: Commit**

```bash
git add scripts/rehearse_demo.py tests/test_docs_contract.py docs/superpowers/evidence/.gitkeep
git commit -m "test: add six-run demo rehearsal evidence"
```

## Task 4: Reconcile plan checkboxes and handoff from observed results

**Files:**
- Modify: `canonpulse-16h-plan.md`, `sessionhandoff.md`, `README.md`
- Test: `tests/test_docs_contract.py`

**Interfaces:**
- `docs/superpowers/plans/2026-07-26-canonpulse-gap-01-ingestion-lifecycle.md` through `...gap-08-documentation-and-demo-closure.md` remain separately linked.
- Handoff records last passing command, commit SHA, deployment ID when applicable, known remaining gap, and next execution plan.

- [ ] **Step 1: Write the failing test**

```python
def test_handoff_links_all_eight_gap_plans_and_last_validation():
    text = Path("sessionhandoff.md").read_text()
    for number in range(1, 9):
        assert f"gap-{number:02d}" in text
    assert "last validation" in text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/test_docs_contract.py -k handoff -v`

Expected: FAIL because the current handoff does not provide a complete eight-gap plan index and validation record.

- [ ] **Step 3: Write minimal implementation**

Add a table linking each plan file to its implementation status and verification command, record the observed full-suite result and deployment state, and leave unverified external rehearsal items clearly marked as pending evidence rather than claiming completion.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --group dev pytest tests/test_docs_contract.py -v`

Expected: PASS with all eight links, disclosure text, commands, and truthful status markers.

- [ ] **Step 5: Commit**

```bash
git add canonpulse-16h-plan.md sessionhandoff.md README.md tests/test_docs_contract.py
git commit -m "docs: close implementation handoff and plan status"
```

## Self-review

- Spec coverage: README/product accuracy, synthetic disclosure, local/governed instructions, safe fallback, six-run rehearsal evidence, plan links, and truthful handoff status are covered by Tasks 1–4.
- Completeness scan: the plan contains no unfinished marker or vague implementation instruction.
- Type consistency: `RehearsalReport` and runbook flags match the script contract; all eight plan filenames are exact.
- Verification: run `uv run --group dev pytest tests/test_docs_contract.py -v` and then execute the runbook’s six-run command against the deployed app.
