from datetime import date

import httpx
import pytest

from tests.conftest import make_settings
from tests.fakes import PLOT_ID, FakeUpstreams, emitter_json, forecast_json, plot_json, soil_json
from upstream import PlotData, PlotNotFound, Upstream, UpstreamError

pytestmark = pytest.mark.anyio

START = date(2026, 11, 16)

REGISTRY_CALLS = [
    ("get_plot", "plot", "x"),
    ("get_soil_mm_per_m", "soil", "loam"),
    ("get_emitter_flow_lph", "emitter", "dripnet-pc-1.0"),
]


def make(**steps) -> tuple[FakeUpstreams, Upstream]:
    fake = FakeUpstreams(**steps)
    return fake, Upstream(make_settings(), fake.client())


# Happy paths


async def test_get_plot_returns_the_plot_fields():
    _, upstream = make()
    plot = await upstream.get_plot(PLOT_ID)
    assert plot == PlotData(
        crop_id="tomato",
        planting_date=date(2026, 3, 1),
        soil_id="loam",
        area_m2=1000.0,
        row_spacing_m=1.5,
        emitter_spacing_m=0.4,
        emitter_id="dripnet-pc-1.0",
        lat=31.25,
        lon=34.79,
    )


async def test_get_soil_and_emitter_values():
    _, upstream = make(soil=soil_json(150), emitter=emitter_json(2.2))
    assert await upstream.get_soil_mm_per_m("loam") == 150.0
    assert await upstream.get_emitter_flow_lph("dripnet-pc-1.0") == 2.2


async def test_get_forecast_returns_days_and_stale_flag():
    _, upstream = make(forecast=forecast_json(START, days=3, et0=4.5, rain=1.0, stale=True))
    forecast = await upstream.get_forecast(31.25, 34.79, 3)
    assert forecast.stale is True
    assert [d.date for d in forecast.days] == [date(2026, 11, 16), date(2026, 11, 17), date(2026, 11, 18)]
    assert all(d.et0_mm == 4.5 and d.rain_mm == 1.0 for d in forecast.days)


async def test_forecast_request_has_lat_lon_and_days():
    fake, upstream = make(forecast=forecast_json(START, days=5))
    await upstream.get_forecast(31.25, 34.79, 5)
    params = fake.calls[0].url.params
    assert params["lat"] == "31.25"
    assert params["lon"] == "34.79"
    assert params["days"] == "5"


@pytest.mark.parametrize("bad_id", ["a/b", "../soils/loam", "..", "x?y=1", "x#frag", "a b"])
async def test_registry_id_cannot_change_the_path(bad_id):
    fake, upstream = make()
    await upstream.get_plot(bad_id)
    request = fake.calls[0]
    assert request.url.host == "registry.test"
    assert request.url.raw_path.startswith(b"/v1/plots/")
    # Exactly one path segment after /v1/plots/, no query smuggled in.
    assert request.url.raw_path.count(b"/") == 3
    assert request.url.query == b""


# Registry failures


@pytest.mark.parametrize("method,field,arg", REGISTRY_CALLS)
@pytest.mark.parametrize(
    "step",
    [500, 503, httpx.ConnectTimeout("t"), httpx.ConnectError("c"), "not-json"],
)
async def test_registry_failures_are_upstream_errors(method, field, arg, step):
    _, upstream = make(**{field: step})
    with pytest.raises(UpstreamError) as caught:
        await getattr(upstream, method)(arg)
    assert caught.value.service == "registry-service"


async def test_plot_404_is_plot_not_found():
    _, upstream = make(plot=404)
    with pytest.raises(PlotNotFound):
        await upstream.get_plot(PLOT_ID)


async def test_soil_404_is_an_upstream_error():
    _, upstream = make(soil=404)
    with pytest.raises(UpstreamError) as caught:
        await upstream.get_soil_mm_per_m("loam")
    assert caught.value.service == "registry-service"


async def test_emitter_404_is_an_upstream_error():
    _, upstream = make(emitter=404)
    with pytest.raises(UpstreamError) as caught:
        await upstream.get_emitter_flow_lph("dripnet-pc-1.0")
    assert caught.value.service == "registry-service"


# Invalid registry bodies


def _without(key):
    body = plot_json()
    del body[key]
    return body


BAD_PLOTS = [
    _without("crop_id"),
    _without("lat"),
    plot_json(area_m2=0),
    plot_json(area_m2=-5),
    plot_json(area_m2="1000"),
    plot_json(area_m2=True),
    plot_json(planting_date="01/03/2026"),
    plot_json(planting_date=20260301),
    plot_json(lat=91),
    plot_json(lon=181),
    plot_json(row_spacing_m=None),
    plot_json(emitter_spacing_m=0),
    plot_json(crop_id=""),
    plot_json(area_m2=10**400),
    ["not", "an", "object"],
]


@pytest.mark.parametrize("body", BAD_PLOTS)
async def test_invalid_plot_body_is_an_upstream_error(body):
    _, upstream = make(plot=body)
    with pytest.raises(UpstreamError) as caught:
        await upstream.get_plot(PLOT_ID)
    assert caught.value.service == "registry-service"


@pytest.mark.parametrize("mm", [0, -1, None, "175", True])
async def test_invalid_soil_body_is_an_upstream_error(mm):
    _, upstream = make(soil=soil_json(mm))
    with pytest.raises(UpstreamError) as caught:
        await upstream.get_soil_mm_per_m("loam")
    assert caught.value.service == "registry-service"


@pytest.mark.parametrize("flow", [0, -1.0, None, "1.0", False])
async def test_invalid_emitter_body_is_an_upstream_error(flow):
    _, upstream = make(emitter=emitter_json(flow))
    with pytest.raises(UpstreamError) as caught:
        await upstream.get_emitter_flow_lph("dripnet-pc-1.0")
    assert caught.value.service == "registry-service"


# Weather failures


@pytest.mark.parametrize(
    "step", [500, 503, 422, httpx.ConnectTimeout("t"), httpx.ConnectError("c"), "not-json"]
)
async def test_weather_failures_are_upstream_errors(step):
    _, upstream = make(forecast=step)
    with pytest.raises(UpstreamError) as caught:
        await upstream.get_forecast(31.25, 34.79, 7)
    assert caught.value.service == "weather-service"


# Invalid weather bodies


def _forecast_with(**changes):
    body = forecast_json(START, days=3)
    body.update(changes)
    return body


def _day_with(index, **changes):
    body = forecast_json(START, days=3)
    body["days"][index].update(changes)
    return body


def _without_stale():
    body = forecast_json(START, days=3)
    del body["stale"]
    return body


BAD_FORECASTS = [
    forecast_json(START, days=0),
    forecast_json(START, days=2),
    forecast_json(START, days=4),
    _day_with(1, et0_mm=None),
    _day_with(1, rain_mm=-0.1),
    _day_with(1, rain_mm=True),
    _day_with(1, et0_mm=float("nan")),
    _day_with(1, et0_mm=float("inf")),
    _day_with(1, et0_mm=10**400),
    _day_with(2, date="2026-11-20"),
    _day_with(1, date="16-11-2026"),
    _day_with(1, date=None),
    _without_stale(),
    _forecast_with(stale="false"),
    _forecast_with(stale=None),
    _forecast_with(days="nope"),
    _forecast_with(days=[None, None, None]),
    ["not", "an", "object"],
]


@pytest.mark.parametrize("body", BAD_FORECASTS)
async def test_invalid_forecast_body_is_an_upstream_error(body):
    fake = FakeUpstreams(forecast=body)
    upstream = Upstream(make_settings(), fake.client())
    with pytest.raises(UpstreamError) as caught:
        await upstream.get_forecast(31.25, 34.79, 3)
    assert caught.value.service == "weather-service"


async def test_error_message_has_no_url():
    _, upstream = make(forecast=httpx.ConnectError("boom http://weather.test/v1/forecast"))
    with pytest.raises(UpstreamError) as caught:
        await upstream.get_forecast(31.25, 34.79, 7)
    assert "://" not in str(caught.value)
    assert str(caught.value).startswith("weather-service is unavailable: ")
    _, upstream = make(plot=httpx.ConnectError("boom http://registry.test/v1/plots/x"))
    with pytest.raises(UpstreamError) as caught:
        await upstream.get_plot(PLOT_ID)
    assert "://" not in str(caught.value)
