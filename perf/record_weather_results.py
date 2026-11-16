"""Write one weather performance result file from a k6 summary export.

Usage, from the repository root:
    k6 run --summary-export path/to/summary.json perf/weather_nfr_2_3.js
    python3 perf/record_weather_results.py path/to/summary.json

Writes perf/results/<UTC time>_weather_v<service version>.md.
"""

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "perf" / "results"
TARGET_MS = 100


@dataclass(frozen=True)
class Evaluation:
    p95_ms: float
    failed_rate: float
    passed: bool


def evaluate(summary: dict) -> Evaluation:
    metrics = summary["metrics"]
    p95 = metrics["http_req_duration"]["p(95)"]
    failed = metrics["http_req_failed"]["value"]
    return Evaluation(p95, failed, passed=p95 < TARGET_MS and failed == 0)


def run(*command: str) -> str:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def service_version() -> str:
    main = (ROOT / "services" / "weather-service" / "main.py").read_text()
    return re.search(r'version="([^"]+)"', main).group(1)


def git_state() -> str:
    commit = run("git", "rev-parse", "--short", "HEAD")
    changes = run("git", "status", "--porcelain", "--", "services/weather-service", "perf")
    return f"{commit} (uncommitted changes)" if changes else commit


def main() -> None:
    summary_path = Path(sys.argv[1])
    result = evaluate(json.loads(summary_path.read_text()))
    # The run ends when the summary file is written, so its modification time is the run time.
    run_time = datetime.fromtimestamp(summary_path.stat().st_mtime, tz=timezone.utc)
    version = service_version()
    lines = [
        f"# Weather performance run: v{version} at {run_time.strftime('%Y-%m-%d %H:%M:%S')} UTC",
        "",
        f"- Service version: {version}",
        f"- Git commit: {git_state()}",
        f"- k6: {run('k6', 'version').split()[1]}",
        "- Scenario: fresh forecast (cache hit, fake provider), 10 requests per second for 60 s (perf/weather_nfr_2_3.js)",
        f"- Target (NFR-2.3): p95 under {TARGET_MS} ms",
        f"- Failed requests: {result.failed_rate * 100:.2f}%",
        "",
        "| Route | p95 (ms) | Result |",
        "| --- | --- | --- |",
        f"| GET /v1/forecast (fresh) | {result.p95_ms:.2f} | {'Pass' if result.passed else 'Fail'} |",
        "",
        f"**Overall: {'Pass' if result.passed else 'Fail'}**",
        "",
    ]
    RESULTS.mkdir(parents=True, exist_ok=True)
    target = RESULTS / f"{run_time.strftime('%Y-%m-%dT%H%M%SZ')}_weather_v{version}.md"
    target.write_text("\n".join(lines))
    print(f"Wrote {target}")


if __name__ == "__main__":
    main()
