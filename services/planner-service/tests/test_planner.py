"""build_plan with fake upstreams: the order of calls, rounding and error reporting."""

import math
from datetime import date

import pytest
from fastapi import HTTPException

from planner import PlanNotFinite, build_plan
from tests.fakes import PLOT_ID, FakeUpstreams, emitter_json, forecast_json, plot_json, soil_json
from upstream import Upstream, UpstreamError

pytestmark = pytest.mark.anyio

START = date(2026, 11, 16)


def make(**steps) -> tuple[FakeUpstreams, Upstream]:
    from tests.conftest import make_settings

    fake = FakeUpstreams(**steps)
    return fake, Upstream(make_settings(), fake.client())


async def test_plan_matches_the_engine():
    # Planted 2026-03-01: far past the season, so Kc is Kc end (0.8) for tomato.
    _, upstream = make()
    result = await build_plan(upstream, PLOT_ID, 7)
    assert result.plot_id == PLOT_ID
    assert len(result.days) == 7
    first = result.days[0]
    assert first.date == START
    assert first.kc == 0.8
    # TAW = 175 x 0.7 = 122.5; no irrigation yet, so the bucket only lost ETc.
    assert first.bucket_mm == round(175 * 0.7 - 3.0 * 0.8, 2)
    assert first.litres == 0 and first.run_minutes == 0


async def test_response_is_rounded_only_at_the_end():
    # Bell pepper planted 30 days before the first forecast day: day 31, Kc = 0.6 + 1/35 x 0.45.
    plot = plot_json(crop_id="bell-pepper", planting_date="2026-10-17")
    _, upstream = make(plot=plot, forecast=forecast_json(START, et0=3.123456))
    result = await build_plan(upstream, PLOT_ID, 7)
    day1, day2 = result.days[0], result.days[1]
    assert day1.et0_mm == 3.12
    assert day1.kc == 0.613
    kc1 = 0.6 + 1 / 35 * 0.45
    kc2 = 0.6 + 2 / 35 * 0.45
    taw = 175 * 0.5
    assert day1.bucket_mm == round(taw - 3.123456 * kc1, 2)
    # The second day uses the unrounded et0 and Kc of both days.
    assert day2.bucket_mm == round(taw - 3.123456 * (kc1 + kc2), 2)


async def test_stale_forecast_marks_every_day_stale():
    _, upstream = make(forecast=forecast_json(START, stale=True))
    result = await build_plan(upstream, PLOT_ID, 7)
    assert all(day.stale for day in result.days)


async def test_calls_soil_emitter_and_forecast_after_the_plot():
    fake, upstream = make(plot=plot_json(lat=12.5, lon=-45.25))
    await build_plan(upstream, PLOT_ID, 7)
    assert fake.calls[0].url.path == f"/v1/plots/{PLOT_ID}"
    paths = {call.url.path for call in fake.calls[1:]}
    assert paths == {"/v1/soils/loam", "/v1/emitters/dripnet-pc-1.0", "/v1/forecast"}
    forecast_call = next(call for call in fake.calls if call.url.path == "/v1/forecast")
    assert forecast_call.url.params["lat"] == "12.5"
    assert forecast_call.url.params["lon"] == "-45.25"
    assert forecast_call.url.params["days"] == "7"


async def test_unknown_crop_is_a_422_that_names_it():
    _, upstream = make(plot=plot_json(crop_id="wheat"))
    with pytest.raises(HTTPException) as caught:
        await build_plan(upstream, PLOT_ID, 7)
    assert caught.value.status_code == 422
    assert "wheat" in caught.value.detail


async def test_registry_failure_is_reported_before_weather_failure():
    _, upstream = make(soil=500, forecast=500)
    with pytest.raises(UpstreamError) as caught:
        await build_plan(upstream, PLOT_ID, 7)
    assert "registry-service" in str(caught.value)


# A small bucket (sand, 20 mm per metre) and a high ET0 make the plan irrigate inside 7 days.
def irrigating(**steps):
    return make(soil=soil_json(20), forecast=forecast_json(START, et0=10.0), **steps)


def all_numbers_finite(result) -> bool:
    return all(
        math.isfinite(value)
        for day in result.days
        for value in (day.et0_mm, day.kc, day.litres, day.run_minutes, day.bucket_mm)
    )


async def test_normal_irrigating_plan_is_finite():
    _, upstream = irrigating()
    result = await build_plan(upstream, PLOT_ID, 7)
    assert any(day.litres > 0 for day in result.days)
    assert all_numbers_finite(result)


async def test_tiny_emitter_flow_raises_plan_not_finite():
    _, upstream = irrigating(emitter=emitter_json(5e-324))
    with pytest.raises(PlanNotFinite):
        await build_plan(upstream, PLOT_ID, 7)


async def test_huge_spacings_raise_plan_not_finite():
    _, upstream = irrigating(plot=plot_json(row_spacing_m=1e200, emitter_spacing_m=1e200))
    with pytest.raises(PlanNotFinite):
        await build_plan(upstream, PLOT_ID, 7)
