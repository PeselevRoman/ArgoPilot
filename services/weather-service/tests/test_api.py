"""The HTTP layer, with a fake provider and a movable clock. No real network."""

import logging
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from main import create_app
from tests.conftest import make_settings
from tests.fakes import FakeClock, FakeProvider, valid_payload

START = datetime(2026, 11, 12, 6, 0, tzinfo=UTC)
TODAY = date(2026, 11, 12)
URL = "/v1/forecast?lat=31.25&lon=34.79&days=7"


@pytest.fixture
def make_client():
    clients = []

    def make(*steps, **settings):
        fake = FakeProvider(*steps)
        clock = FakeClock(START)
        client = TestClient(create_app(make_settings(**settings), fake.transport, clock.now))
        client.__enter__()  # runs the lifespan: builds the service
        clients.append(client)
        return client, fake, clock

    yield make
    for client in clients:
        client.__exit__(None, None, None)


def test_forecast_returns_the_documented_shape(make_client):
    client, _, _ = make_client(valid_payload(TODAY, et0=3.1, rain=0.0))

    response = client.get(URL)

    assert response.status_code == 200
    body = response.json()
    assert body["lat"] == 31.25
    assert body["lon"] == 34.79
    assert body["source"] == "open-meteo"
    assert body["fetched_at"] == "2026-11-12T06:00:00Z"
    assert body["stale"] is False
    assert len(body["days"]) == 7
    assert body["days"][0] == {"date": "2026-11-12", "et0_mm": 3.1, "rain_mm": 0.0}
    assert body["days"][6]["date"] == "2026-11-18"
    assert set(body) == {"lat", "lon", "source", "fetched_at", "stale", "days"}


def test_days_is_cut_to_the_request(make_client):
    client, _, _ = make_client(valid_payload(TODAY))

    assert len(client.get("/v1/forecast?lat=31.25&lon=34.79&days=3").json()["days"]) == 3


def test_fresh_request_does_not_call_the_provider_again(make_client):
    client, fake, _ = make_client(valid_payload(TODAY))

    client.get(URL)
    client.get(URL)

    assert len(fake.calls) == 1


def test_stale_answer_has_stale_true_and_keeps_the_original_fetched_at(make_client):
    client, fake, clock = make_client(valid_payload(TODAY), 500)
    client.get(URL)
    clock.advance(hours=4)

    response = client.get(URL)

    assert response.status_code == 200
    assert response.json()["stale"] is True
    assert response.json()["fetched_at"] == "2026-11-12T06:00:00Z"
    assert len(fake.calls) == 1 + 3


def test_503_when_provider_is_down_and_there_is_no_cache(make_client):
    client, _, _ = make_client(500, retry_after_seconds=60)

    response = client.get(URL)

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "UNAVAILABLE"
    assert response.headers["retry-after"] == "60"


@pytest.mark.parametrize(
    "query",
    [
        "lat=90.1&lon=34.79&days=7",
        "lat=-90.1&lon=34.79&days=7",
        "lat=31.25&lon=180.1&days=7",
        "lat=31.25&lon=-180.1&days=7",
        "lat=31.25&lon=34.79&days=0",
        "lat=31.25&lon=34.79&days=8",
        "lat=31.25&lon=34.79&days=3.5",
        "lat=31.25&lon=34.79&days=abc",
        "lat=abc&lon=34.79&days=7",
        "lat=nan&lon=34.79&days=7",
        "lat=inf&lon=34.79&days=7",
        "lat=31.25&lon=nan&days=7",
        "lon=34.79&days=7",
        "lat=31.25&days=7",
        "lat=31.25&lon=34.79",
    ],
)
def test_validation_errors_are_422_validation(make_client, query):
    client, fake, _ = make_client(valid_payload(TODAY))

    response = client.get(f"/v1/forecast?{query}")

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "VALIDATION"
    assert fake.calls == []


@pytest.mark.parametrize(
    ("lat", "lon"), [(90, 34.79), (-90, 34.79), (31.25, 180), (31.25, -180), (90, 180), (-90, -180)]
)
def test_boundaries_are_accepted_and_the_provider_request_stays_in_range(make_client, lat, lon):
    client, fake, _ = make_client(valid_payload(TODAY))

    response = client.get(f"/v1/forecast?lat={lat}&lon={lon}&days=1")

    assert response.status_code == 200
    params = fake.calls[0].url.params
    assert -90 <= float(params["latitude"]) <= 90
    assert -180 <= float(params["longitude"]) <= 180


@pytest.mark.parametrize("days", [1, 7])
def test_days_boundaries_are_accepted(make_client, days):
    client, _, _ = make_client(valid_payload(TODAY))

    response = client.get(f"/v1/forecast?lat=31.25&lon=34.79&days={days}")

    assert len(response.json()["days"]) == days


def test_unknown_route_is_404_not_found(make_client):
    client, _, _ = make_client(valid_payload(TODAY))

    response = client.get("/v1/nothing")

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
    assert response.headers["content-type"].startswith("application/problem+json")


def test_wrong_method_is_405_problem_json(make_client):
    client, _, _ = make_client(valid_payload(TODAY))

    response = client.post(URL)

    assert response.status_code == 405
    assert response.headers["content-type"].startswith("application/problem+json")


def test_health_is_ok_and_does_not_call_the_provider(make_client):
    client, fake, _ = make_client(500)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert fake.calls == []


def test_response_never_contains_provider_field_names(make_client):
    client, _, _ = make_client(valid_payload(TODAY))

    text = client.get(URL).text

    assert "et0_fao_evapotranspiration" not in text
    assert "precipitation_sum" not in text


def test_app_refuses_to_start_without_settings():
    with pytest.raises(RuntimeError, match="PROVIDER_BASE_URL"):
        with TestClient(create_app()):
            pass


def test_api_key_never_reaches_the_logs_even_at_info_level(make_client, caplog):
    client, _, _ = make_client(valid_payload(TODAY), provider_api_key="SECRET123")

    with caplog.at_level(logging.INFO):
        assert client.get(URL).status_code == 200

    # httpx logs every request line, query string included, at INFO unless told otherwise.
    assert "SECRET123" not in caplog.text
