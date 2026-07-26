from pathlib import Path


def test_index_contains_all_workflow_panels():
    html = Path("app/static/index.html").read_text()
    for panel_id in ("health-panel", "heatmap-panel", "evidence-drawer", "comparison-panel", "cohort-panel", "discovery-panel"):
        assert f'id="{panel_id}"' in html


def test_frontend_has_error_and_retry_states():
    js = Path("app/static/app.js").read_text()
    assert "loading" in js and "retry" in js and "error" in js
