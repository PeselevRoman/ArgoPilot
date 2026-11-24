"""The frontend's request timeout must outlast the planner's own waits.

The planner calls the registry, then the weather service, one after the other. Its limits are
per phase, so their sum is the most it can wait. The frontend's timeout covers the whole call to
the planner, so it has to be longer than that sum. This test reads the example settings of both
services (not the real .env files) and fails if the frontend's value is too short.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def example_values(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            name, value = line.split("=", 1)
            values[name.strip()] = value.strip()
    return values


def test_frontend_timeout_is_longer_than_the_planner_waits_for_its_upstreams():
    planner = example_values(ROOT / "services/planner-service/.env.example")
    frontend = example_values(ROOT / "services/frontend/.env.example")
    planner_wait_ms = (
        float(planner["REGISTRY_TIMEOUT_SECONDS"]) + float(planner["WEATHER_TIMEOUT_SECONDS"])
    ) * 1000
    assert int(frontend["REQUEST_TIMEOUT_MS"]) > planner_wait_ms, (
        f"frontend REQUEST_TIMEOUT_MS ({frontend['REQUEST_TIMEOUT_MS']}) must be longer than "
        f"the planner's waits together ({planner_wait_ms:.0f} ms)"
    )
