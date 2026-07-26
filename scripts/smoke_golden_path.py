"""Run the deployed golden path and fail on missing provenance or latency."""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from dataclasses import dataclass, field


@dataclass
class SmokeResult:
    failures: list[str] = field(default_factory=list)
    checks: list[dict] = field(default_factory=list)

    @property
    def exit_code(self) -> int:
        return 1 if self.failures else 0


@dataclass
class RehearsalReport:
    successful_runs: int
    failures: list[str] = field(default_factory=list)
    run_reports: list[dict] = field(default_factory=list)

    @property
    def exit_code(self) -> int:
        return 1 if self.failures else 0


def run_smoke(base_url: str, series_id: str, version_id: str, max_latency_ms: float = 5000) -> SmokeResult:
    result = SmokeResult()
    paths = ["/health/live", "/health/ready", "/api/series", "/api/audit", "/api/diagnostics"]
    for path in paths:
        started = time.monotonic()
        try:
            request = urllib.request.Request(
                base_url.rstrip("/") + path,
                headers={"X-Series-Id": series_id, "X-Version-Id": version_id},
            )
            with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
                payload = json.loads(response.read().decode())
                status = response.status
        except Exception as exc:  # noqa: BLE001 - smoke converts failures to report entries
            result.failures.append(f"{path}: {type(exc).__name__}")
            continue
        elapsed = (time.monotonic() - started) * 1000
        result.checks.append({"path": path, "status": status, "latency_ms": round(elapsed, 2)})
        if elapsed > max_latency_ms:
            result.failures.append(f"{path}: latency exceeds threshold")
        if path == "/api/diagnostics" and not payload.get("model_version"):
            result.failures.append("model_version")
        if path == "/api/audit" and any(not finding.get("citations") for finding in payload.get("findings", [])):
            result.failures.append("missing citations")
    return result


def run_rehearsal(
    base_url: str,
    series_id: str,
    version_id: str,
    *,
    runs: int = 6,
    run_once=run_smoke,
) -> RehearsalReport:
    failures: list[str] = []
    reports: list[dict] = []
    successful = 0
    for run_number in range(1, runs + 1):
        smoke = run_once(base_url, series_id, version_id)
        reports.append({"run": run_number, "failures": smoke.failures, "checks": smoke.checks})
        if smoke.exit_code == 0:
            successful += 1
        else:
            failures.extend(f"run {run_number}: {failure}" for failure in smoke.failures)
    if successful != 6:
        failures.insert(0, f"six successful runs required; observed {successful}")
    return RehearsalReport(successful_runs=successful, failures=failures, run_reports=reports)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--series-id", default="last-monsoon")
    parser.add_argument("--version-id", default="demo")
    parser.add_argument("--max-latency-ms", type=float, default=5000)
    args = parser.parse_args()
    result = run_rehearsal(args.base_url, args.series_id, args.version_id)
    print(json.dumps({"successful_runs": result.successful_runs, "runs": result.run_reports, "failures": result.failures}, indent=2))
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
