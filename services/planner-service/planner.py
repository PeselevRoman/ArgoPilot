"""The plan: fetch the plot, then its soil, emitter and forecast, then run the engine."""

import asyncio
import datetime
import math

from fastapi import HTTPException
from pydantic import BaseModel

from crops import UnknownCrop, get_crop
from engine import PlotInputs, plan
from upstream import Upstream


class PlanNotFinite(Exception):
    """The engine produced a number that is not finite (inf or nan): never answer it as a plan."""


class PlanDayOut(BaseModel):
    # irrigation_mm (the engine's internal depth) is deliberately not here.
    date: datetime.date
    et0_mm: float
    kc: float
    litres: float
    run_minutes: float
    stale: bool
    bucket_mm: float


class PlanOut(BaseModel):
    plot_id: str
    days: list[PlanDayOut]


async def build_plan(upstream: Upstream, plot_id: str, days: int) -> PlanOut:
    # The plot comes first: the other three calls need its soil, emitter, lat and lon.
    plot = await upstream.get_plot(plot_id)
    try:
        crop = get_crop(plot.crop_id)
    except UnknownCrop as error:
        raise HTTPException(status_code=422, detail=f"The plot's crop is not supported: {error.crop_id}") from None

    # asyncio.gather is like Task.WhenAll in C#: the three calls run at the same time, so the
    # request waits for the slowest one, not for the sum. return_exceptions=True makes gather
    # hand back each failure as a value in the result list, instead of throwing the first one
    # (the other calls would be left running, unobserved).
    results = await asyncio.gather(
        upstream.get_soil_mm_per_m(plot.soil_id),
        upstream.get_emitter_flow_lph(plot.emitter_id),
        upstream.get_forecast(plot.lat, plot.lon, days),
        return_exceptions=True,
    )
    # Trade-off: a fast failure (for example the soil call) still waits for the slowest call, up to
    # the weather timeout. Accepted, to keep the error order deterministic.
    # Re-raise in a fixed order (soil, emitter, forecast): the registry is reported before the
    # weather service, whatever finished first.
    for result in results:
        if isinstance(result, BaseException):
            raise result
    soil_mm_per_m, flow_lph, forecast = results

    inputs = PlotInputs(
        crop=crop,
        planting_date=plot.planting_date,
        area_m2=plot.area_m2,
        row_spacing_m=plot.row_spacing_m,
        emitter_spacing_m=plot.emitter_spacing_m,
        emitter_flow_lph=flow_lph,
        soil_mm_per_m=soil_mm_per_m,
    )
    plan_days = plan(inputs, forecast.days)
    # A finite but absurd registry value can make the engine produce inf; pydantic would
    # serialise it as null (a 200 that reads as "don't water"). Refuse it instead.
    for day in plan_days:
        numbers = (day.et0_mm, day.kc, day.irrigation_mm, day.litres, day.run_minutes, day.bucket_mm)
        if not all(math.isfinite(number) for number in numbers):
            raise PlanNotFinite
    # Rounding happens only here, for display; the engine's state stays unrounded.
    return PlanOut(
        plot_id=plot_id,
        days=[
            PlanDayOut(
                date=day.date,
                et0_mm=round(day.et0_mm, 2),
                kc=round(day.kc, 3),
                litres=round(day.litres, 2),
                run_minutes=round(day.run_minutes, 2),
                stale=day.stale,
                bucket_mm=round(day.bucket_mm, 2),
            )
            for day in plan_days
        ],
    )
