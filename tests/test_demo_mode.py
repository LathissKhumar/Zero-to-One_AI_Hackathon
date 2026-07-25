from __future__ import annotations

from app.demo_mode import INFERENCE_TIMEOUT_SECONDS, golden_path


def test_golden_path_renders_without_any_inference():
    payload = golden_path()
    assert payload["headline"]["baseline_flags"] > payload["headline"]["real_holes"]
    assert payload["findings"]


def test_timeout_is_short_enough_to_switch_before_a_judge_notices():
    assert INFERENCE_TIMEOUT_SECONDS <= 5
