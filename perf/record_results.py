"""Write one performance result file from a k6 summary export.

Usage, from the repository root:
    k6 run --summary-export path/to/summary.json perf/nfr_1_1.js
    python3 perf/record_results.py path/to/summary.json [sqlite|postgresql]

Each run writes perf/results/<UTC time>_v<service version>.md, so the log
keeps every run with its time and the code version it measured.
"""

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "perf" / "results"
TARGET_MS = 100


def dataset_line(engine_name: str) -> str:
    return f"100 farms, 10,000 plots (perf/seed_perf_db.py, seed 42), on {engine_name}"


ENDPOINTS = [
    ("list_farms", "GET /v1/farms"),
    ("get_farm", "GET /v1/farms/{id}"),
    ("list_plots", "GET /v1/plots"),
    ("get_plot", "GET /v1/plots/{id}"),
    ("list_crops", "GET /v1/crops"),
    ("get_crop", "GET /v1/crops/{id}"),
    ("list_soils", "GET /v1/soils"),
    ("get_soil", "GET /v1/soils/{id}"),
    ("list_emitters", "GET /v1/emitters"),
    ("get_emitter", "GET /v1/emitters/{id}"),
]


def run(*command: str) -> str:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def service_version() -> str:
    main = (ROOT / "services" / "registry-service" / "main.py").read_text()
    return re.search(r'version="([^"]+)"', main).group(1)


def git_state() -> str:
    commit = run("git", "rev-parse", "--short", "HEAD")
    changes = run("git", "status", "--porcelain", "--", "services/registry-service", "perf")
    return f"{commit} (uncommitted changes)" if changes else commit


def main() -> None:
    summary_path = Path(sys.argv[1])
    engine_name = sys.argv[2] if len(sys.argv) > 2 else "sqlite"
    summary = json.loads(summary_path.read_text())
    metrics = summary["metrics"]

    # The run ends when the summary file is written, so its modification time is the run time.
    run_time = datetime.fromtimestamp(summary_path.stat().st_mtime, tz=timezone.utc)
    version = service_version()
    failed_rate = metrics["http_req_failed"]["value"]

    rows = []
    all_passed = failed_rate == 0
    for key, label in ENDPOINTS:
        metric = metrics[f"http_req_duration{{endpoint:{key}}}"]
        p95 = metric["p(95)"]
        passed = p95 < TARGET_MS
        all_passed = all_passed and passed
        rows.append(f"| {label} | {p95:.2f} | {'Pass' if passed else 'Fail'} |")

    stamp = run_time.strftime("%Y-%m-%dT%H%M%SZ")
    lines = [
        f"# Performance run: v{version} at {run_time.strftime('%Y-%m-%d %H:%M:%S')} UTC",
        "",
        f"- Service version: {version}",
        f"- Git commit: {git_state()}",
        f"- Run time (UTC): {run_time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- k6: {run('k6', 'version').split()[1]}",
        f"- Dataset: {dataset_line(engine_name)}",
        f"- Target (NFR-1.1): p95 under {TARGET_MS} ms at 10 requests per second, per endpoint",
        f"- Failed requests: {failed_rate * 100:.2f}%",
        "",
        "| Endpoint | p95 (ms) | Result |",
        "| --- | --- | --- |",
        *rows,
        "",
        f"**Overall: {'Pass' if all_passed else 'Fail'}**",
        "",
    ]

    RESULTS.mkdir(parents=True, exist_ok=True)
    target = RESULTS / f"{stamp}_v{version}.md"
    target.write_text("\n".join(lines))
    print(f"Wrote {target}")


if __name__ == "__main__":
    main()
