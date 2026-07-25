# CanonPulse Narrative Debt Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (\`- [ ]\`) syntax for tracking.

**Goal:** Build a local-first, Databricks-deployable narrative-debt comparison app with an evidence-cited Audience Court and DefectLab reliability screen.

**Architecture:** FastAPI serves a single-page dashboard and a JSON API. \`NarrativeDebtEngine\` is the deep module that owns comparison, Audience Court, discovery, and DefectLab; HTTP handlers only invoke it. Demo mode uses original structured data, and Databricks deployment resources are fully parameterized.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, vanilla HTML/CSS/JavaScript, pytest, Databricks Apps, Delta/AI Search/\`ai_query\`, MLflow, Databricks Asset Bundles.

## Global Constraints

- Use original synthetic data only; never claim Pocket FM access, real listener data, or retention uplift.
- Keep canon checking as cited evidence plumbing; pitch narrative debt: pay, defer, renew, or default.
- Show five fixed cohorts and label the court as a pre-release simulation.
- Demo mode requires no credentials. Databricks mode must fail clearly when configuration is absent.
- Parameterize catalog, schema, warehouse, model service, AI Search index, and experiment. Do not hardcode IDs or credentials.
- DefectLab reports measured issue precision/recall, citation support, and structured-output validity.

---

### Task 1: Narrative data and audit engine

**Files:**
- Create: \`pyproject.toml\`, \`.gitignore\`, \`app/__init__.py\`, \`app/models.py\`, \`app/demo_data.py\`, \`app/engine.py\`
- Create: \`tests/test_engine.py\`, \`tests/test_benchmark.py\`

**Interfaces:**
- Produces \`get_demo_story() -> Story\`.
- Produces \`NarrativeDebtEngine.compare(story: Story, left_slug: str, right_slug: str) -> AuditResult\`.
- Produces \`NarrativeDebtEngine.run_benchmark(story: Story) -> BenchmarkResult\`.

- [ ] **Step 1: Write the failing domain test**

\`\`\`python
def test_earned_ending_repays_more_debt_than_shock_ending():
    story = get_demo_story()
    result = NarrativeDebtEngine().compare(story, "shock-default", "earned-storm")
    assert result.winner_slug == "earned-storm"
    assert result.options["earned-storm"].debt_health > result.options["shock-default"].debt_health
    assert result.options["shock-default"].risks[0].evidence
\`\`\`

- [ ] **Step 2: Run it red**

Run: \`uv run --group dev pytest tests/test_engine.py -q\`

Expected: FAIL because \`app.demo_data\` and \`app.engine\` do not exist.

- [ ] **Step 3: Implement the smallest complete audit module**

\`\`\`python
class NarrativeDebtEngine:
    def compare(self, story: Story, left_slug: str, right_slug: str) -> AuditResult:
        options = {slug: self._audit(story, slug) for slug in (left_slug, right_slug)}
        return AuditResult(
            winner_slug=max(options, key=lambda slug: options[slug].debt_health),
            options=options,
            court=self._court(story, options),
        )
\`\`\`

Seed an original eight-episode story, six narrative debts, two creator-written endings, five cohorts, and twelve labelled evaluation cases. Every debt risk must cite at least one episode excerpt. Compute Debt Health from explicit paid, renewed, deferred, and defaulted debt actions; do not output a retention percentage.

- [ ] **Step 4: Add benchmark test and make both tests green**

\`\`\`python
def test_defect_lab_reports_measured_reliability():
    benchmark = NarrativeDebtEngine().run_benchmark(get_demo_story())
    assert benchmark.recall == 1.0
    assert benchmark.precision == 1.0
    assert benchmark.citation_support_rate == 1.0
\`\`\`

Run: \`uv run --group dev pytest tests/test_engine.py tests/test_benchmark.py -q\`

Expected: PASS.

- [ ] **Step 5: Commit**

\`\`\`bash
git add pyproject.toml .gitignore app tests uv.lock
git commit -m "feat: add narrative debt audit engine"
\`\`\`

### Task 2: HTTP interface and Mood-to-Debt discovery

**Files:**
- Create: \`app/main.py\`, \`tests/test_api.py\`, \`tests/test_discovery.py\`

**Interfaces:**
- Produces \`create_app() -> FastAPI\`.
- Produces \`GET /api/story\`, \`POST /api/compare\`, \`GET /api/benchmark\`, and \`GET /api/discover?q=...\`.

- [ ] **Step 1: Write failing public-interface tests**

\`\`\`python
def test_compare_endpoint_returns_a_cited_court_verdict(client):
    response = client.post("/api/compare", json={"left_slug": "shock-default", "right_slug": "earned-storm"})
    assert response.status_code == 200
    assert response.json()["winner_slug"] == "earned-storm"
    assert len(response.json()["court"]) == 5

def test_mood_discovery_explains_its_match(client):
    response = client.get("/api/discover", params={"q": "rainy Sunday after heartbreak"})
    assert response.status_code == 200
    assert "why" in response.json()[0]
\`\`\`

- [ ] **Step 2: Run them red**

Run: \`uv run --group dev pytest tests/test_api.py tests/test_discovery.py -q\`

Expected: FAIL because \`create_app\` does not exist.

- [ ] **Step 3: Implement focused handlers**

\`\`\`python
@app.post("/api/compare")
def compare(payload: CompareRequest) -> AuditResult:
    return engine.compare(get_demo_story(), payload.left_slug, payload.right_slug)
\`\`\`

Discovery ranks six synthetic catalogue entries by emotional-debt tags, then returns a source-backed \`why\` field. Invalid ending slugs return HTTP 422 with the permitted slugs.

- [ ] **Step 4: Run the API tests green**

Run: \`uv run --group dev pytest tests/test_api.py tests/test_discovery.py -q\`

Expected: PASS.

- [ ] **Step 5: Commit**

\`\`\`bash
git add app/main.py tests/test_api.py tests/test_discovery.py
git commit -m "feat: add audit and discovery APIs"
\`\`\`

### Task 3: Audience Court dashboard

**Files:**
- Create: \`app/static/index.html\`, \`app/static/styles.css\`, \`app/static/app.js\`
- Modify: \`app/main.py\`, \`tests/test_api.py\`

**Interfaces:**
- Consumes the Task 2 endpoints.
- Produces a single-page dashboard with comparison, five court cards, evidence cards, DefectLab, and a discovery panel.

- [ ] **Step 1: Write the failing browser smoke test**

\`\`\`python
def test_root_serves_the_canonpulse_dashboard(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Narrative Debt Engine" in response.text
    assert "Audience Court" in response.text
\`\`\`

- [ ] **Step 2: Run it red**

Run: \`uv run --group dev pytest tests/test_api.py::test_root_serves_the_canonpulse_dashboard -q\`

Expected: FAIL because no static application is mounted.

- [ ] **Step 3: Implement the dashboard**

\`\`\`javascript
async function compare() {
  const result = await fetch("/api/compare", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({left_slug: "shock-default", right_slug: "earned-storm"})
  }).then(response => response.json());
  renderComparison(result);
}
\`\`\`

Use a dark cinematic palette, a large “what the story owes” headline, creator-supplied ending cards, visible simulation disclosure, evidence citations, five distinctive jurors, and no fake retention percentages.

- [ ] **Step 4: Run dashboard and full tests green**

Run: \`uv run --group dev pytest -q\`

Expected: PASS.

- [ ] **Step 5: Commit**

\`\`\`bash
git add app/static app/main.py tests/test_api.py
git commit -m "feat: add Audience Court dashboard"
\`\`\`

### Task 4: Databricks-native assets

**Files:**
- Create: \`app.yaml\`, \`databricks.yml\`, \`resources/canonpulse.app.yml\`, \`sql/bootstrap.sql\`, \`sql/audience_court.sql\`, \`tests/test_databricks_assets.py\`

**Interfaces:**
- Consumes variables \`catalog\`, \`schema\`, \`warehouse_id\`, \`court_model\`, \`ai_search_index\`, and \`mlflow_experiment_id\`.
- Produces a Databricks App, DAB, Delta/AI Search bootstrap workflow, and an \`ai_query\` Court query.

- [ ] **Step 1: Write the failing configuration test**

\`\`\`python
def test_databricks_assets_are_parameterized_and_use_ai_query():
    bundle = Path("databricks.yml").read_text()
    court = Path("sql/audience_court.sql").read_text()
    assert "\${var.catalog}" in bundle
    assert "ai_query" in court
    assert "OPENAI_API_KEY=" not in bundle
\`\`\`

- [ ] **Step 2: Run it red**

Run: \`uv run --group dev pytest tests/test_databricks_assets.py -q\`

Expected: FAIL because the deployment assets do not exist.

- [ ] **Step 3: Implement the parameterized SQL and bundle**

\`\`\`sql
SELECT cohort_id, ai_query(
  '\${var.court_model}',
  concat(draft_context, '\\nCohort: ', preference_profile),
  responseFormat => 'STRUCT<vote:STRING,debt_status:STRING,fairness:DOUBLE,urgency:DOUBLE,reason:STRING,citation_ids:ARRAY<STRING>>'
) AS verdict
FROM \${var.catalog}.\${var.schema}.audience_cohorts;
\`\`\`

Set \`DEMO_MODE=true\` in \`app.yaml\` for the first deployment. The bundle must parameterize resource names and include an App resource without secrets or direct token values.

- [ ] **Step 4: Run configuration and full tests green**

Run: \`uv run --group dev pytest -q\`

Expected: PASS.

- [ ] **Step 5: Commit**

\`\`\`bash
git add app.yaml databricks.yml resources sql tests/test_databricks_assets.py
git commit -m "feat: add Databricks deployment assets"
\`\`\`

### Task 5: Verify and hand off

**Files:**
- Create: \`README.md\`

**Interfaces:**
- Consumes all application and deployment assets.
- Produces local run instructions, Databricks prerequisites, and a 90-second judge demo.

- [ ] **Step 1: Run source compilation and tests**

Run: \`uv run python -m compileall app && uv run --group dev pytest -q\`

Expected: all files compile and all tests pass.

- [ ] **Step 2: Run the HTTP interface**

Run: \`uv run uvicorn app.main:app --host 127.0.0.1 --port 8000\`

In another terminal:

\`\`\`bash
curl -s http://127.0.0.1:8000/api/benchmark
curl -s -X POST http://127.0.0.1:8000/api/compare -H 'Content-Type: application/json' -d '{"left_slug":"shock-default","right_slug":"earned-storm"}'
\`\`\`

Expected: benchmark metrics and an evidence-cited five-member Court verdict.

- [ ] **Step 3: Document the exact demo sequence**

\`\`\`markdown
1. Show the open narrative-debt ledger.
2. Compare the two creator-written endings.
3. Open two disagreeing Court verdicts and their citations.
4. Reveal the winner and minimal safe edits.
5. Show DefectLab measured reliability.
6. Search “rainy Sunday after heartbreak.”
\`\`\`

- [ ] **Step 4: Commit**

\`\`\`bash
git add README.md
git commit -m "docs: add local run and judge demo guide"
\`\`\`

## Plan self-review

- Spec coverage: Tasks 1-2 cover the debt engine, Court, DefectLab, and discovery; Task 3 builds the visual demo; Task 4 makes Databricks deployment and batch \`ai_query\` visible; Task 5 verifies and documents handoff.
- Placeholder scan: no unspecified tasks, error paths, or test behavior remain.
- Type consistency: public handlers consume only the engine, \`Story\`, and ending slug interfaces defined in Task 1.
