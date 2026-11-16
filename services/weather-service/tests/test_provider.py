import copy
import json
from datetime import date

import httpx
import pytest

import provider
from tests.conftest import make_settings
from tests.fakes import FakeProvider, valid_payload

FIRST = date(2026, 7, 1)
ET0 = "et0_fao_evapotranspiration"
RAIN = "precipitation_sum"


def test_parse_returns_nine_days_and_offset():
    payload = valid_payload(FIRST, offset=7200, et0=3.5, rain=1.25)
    forecast = provider.parse_response(payload)
    assert forecast.utc_offset_seconds == 7200
    assert len(forecast.days) == 9
    assert forecast.days[0].date == FIRST
    assert forecast.days[8].date == date(2026, 7, 9)
    assert all(d.et0_mm == 3.5 and d.rain_mm == 1.25 for d in forecast.days)


def _mutate(fn):
    payload = valid_payload(FIRST)
    fn(payload)
    return payload


def _daily(key, value):
    return lambda p: p["daily"].__setitem__(key, value)


INVALID = {
    "not_a_dict": [1, 2, 3],
    "daily_missing": _mutate(lambda p: p.pop("daily")),
    "list_missing": _mutate(lambda p: p["daily"].pop(RAIN)),
    "null_et0": _mutate(lambda p: p["daily"][ET0].__setitem__(2, None)),
    "null_rain": _mutate(lambda p: p["daily"][RAIN].__setitem__(2, None)),
    "string_value": _mutate(lambda p: p["daily"][ET0].__setitem__(1, "3.0")),
    "boolean_value": _mutate(lambda p: p["daily"][RAIN].__setitem__(1, True)),
    "negative_et0": _mutate(lambda p: p["daily"][ET0].__setitem__(0, -0.1)),
    "negative_rain": _mutate(lambda p: p["daily"][RAIN].__setitem__(0, -1)),
    "nan": _mutate(lambda p: p["daily"][ET0].__setitem__(0, float("nan"))),
    "infinity": _mutate(lambda p: p["daily"][RAIN].__setitem__(0, float("inf"))),
    "unequal_lengths": _mutate(lambda p: p["daily"][RAIN].pop()),
    "eight_days": valid_payload(FIRST, days=8),
    "ten_days": valid_payload(FIRST, days=10),
    "not_iso_date": _mutate(lambda p: p["daily"]["time"].__setitem__(3, "03/07/2026")),
    "date_gap": _mutate(lambda p: p["daily"]["time"].__setitem__(4, "2026-07-06")),
    "unit_cm": _mutate(lambda p: p["daily_units"].__setitem__(ET0, "cm")),
    "units_missing": _mutate(lambda p: p.pop("daily_units")),
    "offset_missing": _mutate(lambda p: p.pop("utc_offset_seconds")),
}


@pytest.mark.parametrize("payload", INVALID.values(), ids=INVALID.keys())
def test_parse_refuses_invalid_payload(payload):
    with pytest.raises(provider.ProviderError):
        provider.parse_response(payload)


def test_parse_refuses_nan_literal_from_json_text():
    text = json.dumps(valid_payload(FIRST)).replace('"et0_fao_evapotranspiration": [3.0', '"et0_fao_evapotranspiration": [NaN', 1)
    assert "NaN" in text
    with pytest.raises(provider.ProviderError):
        provider.parse_response(json.loads(text))


@pytest.mark.anyio
@pytest.mark.parametrize("key", ["", "KEY42"])
async def test_fetch_sends_the_documented_request(key):
    fake = FakeProvider(valid_payload(FIRST))
    async with fake.client() as client:
        forecast = await provider.fetch(client, make_settings(provider_api_key=key), 48.85, 2.35)
    assert len(forecast.days) == 9
    assert len(fake.calls) == 1
    request = fake.calls[0]
    assert request.method == "GET"
    assert request.url.path == "/v1/forecast"
    params = dict(request.url.params)
    assert params["latitude"] == "48.85"
    assert params["longitude"] == "2.35"
    assert params["daily"] == "et0_fao_evapotranspiration,precipitation_sum"
    assert params["forecast_days"] == "9"
    assert params["timezone"] == "auto"
    if key:
        assert params["apikey"] == key
    else:
        assert "apikey" not in params


@pytest.mark.anyio
@pytest.mark.parametrize(
    "step",
    [500, 400, "not-json", httpx.ConnectTimeout("t"), httpx.ConnectError("c")],
    ids=["500", "400", "not-json", "timeout", "connect-error"],
)
async def test_fetch_failure_becomes_provider_error(step):
    fake = FakeProvider(step)
    async with fake.client() as client:
        with pytest.raises(provider.ProviderError):
            await provider.fetch(client, make_settings(), 1.0, 2.0)


@pytest.mark.anyio
async def test_provider_error_message_has_no_secret():
    fake = FakeProvider(500)
    async with fake.client() as client:
        with pytest.raises(provider.ProviderError) as info:
            await provider.fetch(client, make_settings(provider_api_key="SECRET123"), 1.0, 2.0)
    message = str(info.value)
    assert "SECRET123" not in message
    assert "provider.test" not in message
    assert "?" not in message
