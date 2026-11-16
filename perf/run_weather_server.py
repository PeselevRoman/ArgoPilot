"""Start weather-service against a fake provider, for the performance check (NFR-2.3).

The check measures the answer from the cache, so no real provider is needed (and
the measurement does not depend on the internet). The service code is not changed:
this launcher only builds the app with a fake provider and the settings below.

Usage, from the repository root, with the weather service's own Python:
    services/weather-service/.venv/bin/python perf/run_weather_server.py

Serves on port 8011 (the registry's performance server uses 8001).
"""

import datetime
import sys
from pathlib import Path

SERVICE = Path(__file__).resolve().parent.parent / "services" / "weather-service"
sys.path.insert(0, str(SERVICE))

import httpx  # noqa: E402

PORT = 8011
OFFSET = 7200


def fake_payload(first_day: datetime.date, days: int = 9) -> dict:
    """An Open-Meteo-shaped answer with plausible numbers."""
    dates = [first_day + datetime.timedelta(days=i) for i in range(days)]
    return {
        "utc_offset_seconds": OFFSET,
        "daily_units": {
            "time": "iso8601",
            "et0_fao_evapotranspiration": "mm",
            "precipitation_sum": "mm",
        },
        "daily": {
            "time": [d.isoformat() for d in dates],
            "et0_fao_evapotranspiration": [2.5 + 0.1 * i for i in range(days)],
            "precipitation_sum": [0.0] * days,
        },
    }


def _handler(request: httpx.Request) -> httpx.Response:
    local_today = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=OFFSET)).date()
    return httpx.Response(200, json=fake_payload(local_today))


def build_app():
    from config import Settings
    from main import create_app

    settings = Settings(
        _env_file=None,
        provider_base_url="http://fake-provider.perf",
        provider_api_key="",
        provider_timeout_seconds=5,
        provider_retries=2,
        provider_retry_delay_seconds=0,
        freshness_hours=3,
        max_stale_hours=24,
        retry_after_seconds=60,
    )
    return create_app(settings, transport=httpx.MockTransport(_handler))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(build_app(), host="127.0.0.1", port=PORT, log_level="warning")
