# Repository Guidelines

## Project Structure

- `app/` contains the FastAPI service and domain logic. `ledger.py`, `extraction.py`, and `narrative_models.py` implement the narrative graph; `predictor.py` and `rewrite.py` expose scoring and repair attribution. Browser assets live in `app/static/`.
- `tests/` contains the pytest suite, with one or more focused `test_*.py` modules per feature.
- `data/` holds the committed demo series and manifest. `scripts/` contains offline generation and opt-in LLM measurement tools.
- `sql/`, `databricks.yml`, `resources/`, and `app.yaml` define Databricks deployment assets. Design notes and plans are under `docs/superpowers/`.

## Build, Test, and Development Commands

Use Python 3.11–3.14 and `uv`:

```bash
uv sync
uv run --group dev pytest
uv run uvicorn app.main:app --port 8000
```

The first command installs locked dependencies, the second runs all tests, and the third starts the local demo at `http://127.0.0.1:8000`. Run a focused test with `uv run --group dev pytest tests/test_ledger.py`. Regenerate the deterministic demo data only when intentionally changing its fixture: `uv run python scripts/generate_series.py`.

## Coding Style & Naming

Follow existing Python style: four-space indentation, type hints, small modules, and descriptive docstrings for domain behavior. Use `snake_case` for functions and variables, `PascalCase` for Pydantic models/classes, and `UPPER_SNAKE_CASE` for constants. Keep feature-vector ordering and API schemas explicit and tested. No formatter or linter is configured; match surrounding code and keep imports clean.

## Testing Guidelines

Tests use pytest and FastAPI’s `TestClient`; test files and functions are named `test_*.py` and `test_*`. Run the full suite before submitting changes. There is no configured coverage threshold, but new behavior should include focused unit or API tests, especially for ledger states, citations, prediction disclosures, and rewrite attribution. Do not add tests that depend on network access or real credentials.

## Commits & Pull Requests

Recent commits use concise Conventional-Commit-style prefixes such as `feat:`, `fix:`, and `docs:` (for example, `fix: validate payoff citations`). Keep commits focused and describe the user-visible or correctness impact. Pull requests should explain the change, list validation commands, link the relevant issue or design note when applicable, and include screenshots for UI changes. Call out Databricks or schema changes explicitly.

## Security & Configuration

Never commit `.env`, tokens, model keys, workspace URLs containing secrets, or generated `mlruns/` data. Local demo mode is offline and uses committed synthetic data; LLM measurement is opt-in, can incur API cost, and must use environment variables. Preserve the project’s explicit disclosure that predictions and cohort reactions are synthetic, not real reader behavior.
