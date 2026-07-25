# CanonPulse — Narrative Debt Engine

> Every clue, vow, wound, threat, and romance arc borrows listener attention. CanonPulse shows creators what their story owes before a new episode is released.

CanonPulse is a pre-release decision system for serialized audio fiction. It compares two creator-supplied endings using an evidence-cited narrative-debt ledger and a five-person Audience Court. It does **not** claim access to Pocket FM, real audience telemetry, or a validated retention model.

## What the demo proves

- **Narrative debt, not generic continuity:** CanonPulse tracks mysteries, causal clues, relationship obligations, emotional wounds, and genre contracts as promises made to listeners.
- **Comparative decision:** it asks which author-written ending pays, renews, defers, or defaults on those promises.
- **Audience Court:** fixed, transparent listener cohorts react to the same cited evidence. Their verdict is labelled a pre-release simulation.
- **DefectLab:** six labelled defect probes plus two clean controls in a fully original demo corpus generate measured precision, recall, citation support, and schema-validity results.
- **Mood-to-Debt Discovery:** a small second view shows how emotional-promise metadata can power “rainy Sunday after heartbreak” discovery and explainability.

## Run locally

No API key is needed for the local demo.

```bash
cd /home/lathiss/Projects/Practice/canonpulse
uv sync --group dev
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

Run verification:

```bash
uv run python -m compileall app
uv run --group dev python -m pytest -q
curl -s http://127.0.0.1:8000/api/benchmark
curl -s -X POST http://127.0.0.1:8000/api/compare \
  -H 'Content-Type: application/json' \
  -d '{"left_slug":"shock-default","right_slug":"earned-storm"}'
```

## 90-second judge demo

1. Open *The Last Monsoon* and point to the open narrative-debt count.
2. Explain: “Pocket CoPilot helps writers produce episodes. CanonPulse tells them whether the series can afford the next one.”
3. Compare **The Surprise Villain** with **The Earned Storm**.
4. Show that Ending A defaults on the cassette, ticket-stub, and Tara-water contracts; open its episode citations.
5. Run the Audience Court and open the Mystery Purist versus the Late-Night Listener verdicts.
6. Reveal Ending B’s producer verdict and one minimal safe edit.
7. Show DefectLab’s measured audit scorecard.
8. Search “rainy Sunday after heartbreak” to show the same promise model powering discovery and “why you’ll love this.”

## Databricks implementation path

The project was initialized with the Databricks AI Dev Kit’s AI/ML and app-development skill packs. The deployment assets deliberately use Databricks as a load-bearing system rather than a decorative store:

| Asset | Role |
|---|---|
| `sql/bootstrap.sql` | Delta tables for episodes, claims, debts, cohorts, and court verdicts |
| AI Search | Retrieve source episode segments and metadata for cited findings |
| `sql/audience_court.sql` | Batch the Audience Court over the cohort table through structured `ai_query` |
| MLflow | Trace retrieval, audit, and court operations; run DefectLab evaluation |
| Unity AI Gateway | Optional governed model routing, inference logging, usage tracking, budgets, and guardrails |
| `databricks.yml` + `resources/` | Databricks App deployment through Asset Bundles |

### Prerequisites for an actual Databricks deployment

- Databricks CLI authenticated to a workspace with Unity Catalog.
- A catalog and schema approved by the workspace owner.
- Permission to create/use a Databricks App, SQL warehouse, MLflow experiment, Delta tables, and AI Search index.
- A serverless SQL warehouse and a supported model-serving region for `ai_query`.
- Unity AI Gateway enabled by an administrator if you want governed Foundation Model inference, inference tables, or budgets.

Do not put a Databricks token, OpenAI key, or Pocket FM credential in this repository.

### Deploy outline

1. Authenticate: `databricks auth login --profile DEFAULT`.
2. Choose a real Unity Catalog and schema; replace `${catalog}` and `${schema}` in a copy of `sql/bootstrap.sql`, then execute it in Databricks SQL.
3. Populate the original demo story into `episodes`, `story_claims`, `narrative_debts`, and `audience_cohorts`.
4. Create a Delta Sync AI Search index over episode segments, syncing story and episode metadata.
5. Select a Databricks model service that supports structured outputs, then run `sql/audience_court.sql` after replacing its DAB variables.
6. Add the AI Search index, SQL warehouse, and MLflow experiment as Databricks App resources. Switch `DEMO_MODE` to `false` only after those resources are configured.
7. Validate and deploy:

```bash
databricks bundle validate -t dev
databricks bundle deploy -t dev
databricks bundle run canonpulse -t dev
```

## Product boundaries

- The Audience Court is a bounded creative simulation, not a panel of real people and not a retention predictor.
- DefectLab validates the audit against intentionally labelled test cases; it does not validate audience behavior.
- The direct OpenAI API can be added as a local failover, but the production route should use a configured Databricks model service with MLflow tracing and, where enabled, Unity AI Gateway governance.
- Pocket FM credentials are not required for this demo. A production integration would need their explicit APIs, data contracts, and permission model.
