from __future__ import annotations

from scripts.smoke_golden_path import SmokeResult, run_rehearsal


def test_rehearsal_report_requires_six_successful_runs():
    report = run_rehearsal("http://unused", "s", "v", runs=5, run_once=lambda *args: SmokeResult())
    assert report.exit_code == 1
    assert "six successful runs" in report.failures[0]


def test_rehearsal_report_succeeds_for_six_clean_runs():
    report = run_rehearsal("http://unused", "s", "v", runs=6, run_once=lambda *args: SmokeResult())
    assert report.exit_code == 0
    assert report.successful_runs == 6
