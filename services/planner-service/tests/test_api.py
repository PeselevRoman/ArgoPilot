"""The HTTP layer with fake upstreams. No real network."""

from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient

from main import create_app
from tests.conftest import SETTING_VARIABLES, make_settings
from tests.fakes import PLOT_ID, FakeUpstreams, forecast_json

START = date(2026, 11, 16)
URL = f"/v1/plots/{PLOT_ID}/plan"
DAY_FIELDS = {"date", "et0_mm", "kc", "litres", "run_minutes", "stale", "bucket_mm"}


@pytest.fixture
def make_client():
    clients = []

    def make(**steps):
        fake = FakeUpstreams(**steps)
        client = TestClient(create_app(make_settings(), fake.transport))
        client.__enter__()  # runs the lifespan: opens the HTTP client
        clients.append(client)
        return client, fake

    yield make
    for client in clients:
        client.__exit__(None, None, None)


def test_plan_has_the_documented_shape(make_client):
    client, _ = make_client()
    response = client.get(URL)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"plot_id", "days"}
    assert body["plot_id"] == PLOT_ID
    assert len(body["days"]) == 7
    for day in body["days"]:
        assert set(day) == DAY_FIELDS
    assert body["days"][0]["date"] == "2026-11-16"


def test_days_default_is_seven(make_client):
    client, fake = make_client()
    assert len(client.get(URL).json()["days"]) == 7
    forecast_call = next(c for c in fake.calls if c.url.path == "/v1/forecast")
    assert forecast_call.url.params["days"] == "7"


@pytest.mark.parametrize("days", [1, 2, 3, 4, 5, 6, 7])
def test_days_can_be_one_to_seven(make_client, days):
    client, _ = make_client(forecast=forecast_json(START, days=days))
    response = client.get(URL, params={"days": days})
    assert response.status_code == 200
    assert len(response.json()["days"]) == days


@pytest.mark.parametrize("days", ["0", "8", "abc", "3.5", "", "-1"])
def test_bad_days_is_422_validation(make_client, days):
    client, fake = make_client()
    response = client.get(f"{URL}?days={days}")
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION"
    assert fake.calls == []


def test_unknown_plot_is_404_not_found(make_client):
    client, _ = make_client(plot=404)
    response = client.get(URL)
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
    assert "days" not in response.json()


def test_malformed_plot_id_is_404(make_client):
    client, _ = make_client(plot=404)
    response = client.get("/v1/plots/not-a-uuid/plan")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


@pytest.mark.parametrize("step", [500, httpx.ReadTimeout("slow"), "not-json"])
def test_registry_down_is_503_upstream_unavailable_naming_it(make_client, step):
    client, _ = make_client(plot=step)
    response = client.get(URL)
    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "UPSTREAM_UNAVAILABLE"
    assert "registry-service" in body["detail"]


WEATHER_FAILURES = [
    503,
    httpx.ReadTimeout("slow"),
    "not-json",
    forecast_json(START, days=0),
    {**forecast_json(START), "days": [{"date": "2026-11-16", "et0_mm": None, "rain_mm": None}] * 7},
]


@pytest.mark.parametrize("step", WEATHER_FAILURES)
def test_weather_down_is_503_upstream_unavailable_naming_it(make_client, step):
    client, _ = make_client(forecast=step)
    response = client.get(URL)
    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "UPSTREAM_UNAVAILABLE"
    assert "weather-service" in body["detail"]


@pytest.mark.parametrize("step", WEATHER_FAILURES)
def test_never_a_plan_of_zeros_when_weather_fails(make_client, step):
    client, _ = make_client(forecast=step)
    assert "days" not in client.get(URL).json()


def test_stale_forecast_still_gives_a_plan(make_client):
    client, _ = make_client(forecast=forecast_json(START, stale=True))
    response = client.get(URL)
    assert response.status_code == 200
    assert all(day["stale"] is True for day in response.json()["days"])


def test_registry_failure_beats_weather_failure_in_the_detail(make_client):
    client, _ = make_client(soil=500, forecast=503)
    response = client.get(URL)
    assert response.status_code == 503
    assert "registry-service" in response.json()["detail"]


def test_problem_json_content_type_on_every_error(make_client):
    client, _ = make_client(forecast=503)
    responses = [
        client.get(URL),
        client.get(f"{URL}?days=0"),
        client.get("/nope"),
        client.post(URL),
    ]
    for response in responses:
        assert response.headers["content-type"].startswith("application/problem+json")


def test_health_ok_and_calls_nothing(make_client):
    client, fake = make_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert fake.calls == []


def test_unknown_route_404_not_found(make_client):
    client, _ = make_client()
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_wrong_method_405(make_client):
    client, _ = make_client()
    response = client.post(URL)
    assert response.status_code == 405
    assert response.json()["code"] == "VALIDATION"


def test_app_refuses_to_start_without_settings(monkeypatch):
    for name in SETTING_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(RuntimeError, match="REGISTRY_URL"):
        with TestClient(create_app()):
            pass
