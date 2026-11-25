"""Tests for the weather performance tooling. Run with the weather service's own Python:

    services/weather-service/.venv/bin/python -m pytest perf/tests/test_weather_perf.py -q
"""

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "services" / "weather-service"))
sys.path.insert(0, str(ROOT / "perf"))

import provider  # noqa: E402  (the weather service's validator)
import record_weather_results  # noqa: E402
import run_weather_server  # noqa: E402


def test_fake_payload_is_accepted_by_the_real_validator():
    forecast = provider.parse_response(run_weather_server.fake_payload(date(2026, 11, 12)))

    assert len(forecast.days) == provider.FETCH_DAYS
    assert forecast.days[0].date == date(2026, 11, 12)


def test_result_passes_under_the_target():
    summary = {"metrics": {"http_req_duration": {"p(95)": 12.5}, "http_req_failed": {"value": 0}}}

    result = record_weather_results.evaluate(summary)

    assert result.p95_ms == 12.5
    assert result.passed is True


def test_result_fails_at_or_over_the_target():
    summary = {"metrics": {"http_req_duration": {"p(95)": 100.0}, "http_req_failed": {"value": 0}}}

    assert record_weather_results.evaluate(summary).passed is False


def test_result_fails_when_requests_failed():
    summary = {"metrics": {"http_req_duration": {"p(95)": 5.0}, "http_req_failed": {"value": 0.01}}}

    assert record_weather_results.evaluate(summary).passed is False
