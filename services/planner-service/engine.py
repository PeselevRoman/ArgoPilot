"""The irrigation engine: the pure calculation behind every irrigation number of a plan.

It follows .claude/skills/irrigation-calc-reference/SKILL.md exactly, which follows FAO-56
(FAO Irrigation and Drainage Paper 56, Allen et al., 1998; the research with the chapter and
table for each claim is docs/research/fao56.md). No AI model computes or adjusts these numbers.

"Pure" means: the output depends only on the arguments. No network, no files, no clock, no
global state. In C# terms it is a static class of static methods over readonly records, so it
is trivial to unit-test: same inputs, same outputs, every time. The caller (the API layer)
fetches the plot and the forecast and decides what "today" is; the engine only calculates.

Units: every depth (ET0, ETc, rain, depletion, bucket level, irrigation) is in mm of water.
1 mm of water over 1 m2 is 1 litre.

Rounding: none here. Every value stays a full-precision float. Rounding inside the loop would
carry a small error from one day into the next (like accumulating a rounded deltaTime in a game
loop), so the response layer rounds once, at the end, for display only.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from crops import Crop


@dataclass(frozen=True)
class ForecastDay:
    date: date
    et0_mm: float
    rain_mm: float
    stale: bool


@dataclass(frozen=True)
class PlotInputs:
    """Everything the engine needs to know about one plot (a C# readonly record)."""

    crop: Crop
    planting_date: date
    area_m2: float
    row_spacing_m: float
    emitter_spacing_m: float
    emitter_flow_lph: float  # litres per hour, per emitter
    soil_mm_per_m: float  # available water: mm of water per metre of soil depth


@dataclass(frozen=True)
class PlanDay:
    """One day of the plan, in full precision.

    irrigation_mm is internal: the API returns litres and run_minutes, not the depth.
    """

    date: date
    et0_mm: float
    kc: float
    irrigation_mm: float
    litres: float
    run_minutes: float
    stale: bool
    bucket_mm: float


def _day_number(planting_date: date, day: date) -> int:
    """Day number i: the planting day is day 1. A planting date after `day` counts as day 1."""
    return max(1, (day - planting_date).days + 1)


def kc_for(crop: Crop, planting_date: date, day: date) -> float:
    """The crop coefficient Kc on `day`: a piecewise-linear curve over the season.

    FAO-56 Ch. 6, Fig. 25 and Eq. 66 (linear interpolation between stage values).
    Kc scales the reference evapotranspiration ET0 to this crop at this growth stage.
    """
    i = _day_number(planting_date, day)
    l_ini, l_dev, l_mid, l_late = crop.stage_days
    end_dev = l_ini + l_dev
    end_mid = end_dev + l_mid
    end_late = end_mid + l_late

    if i <= l_ini:
        # Initial stage: flat at Kc_ini.
        return crop.kc_ini
    if i <= end_dev:
        # Development: Eq. 66, rising linearly from Kc_ini to Kc_mid (reaches Kc_mid on the last day).
        return crop.kc_ini + (i - l_ini) / l_dev * (crop.kc_mid - crop.kc_ini)
    if i <= end_mid:
        # Mid-season: flat at Kc_mid.
        return crop.kc_mid
    if i <= end_late:
        # Late season: Eq. 66, falling linearly from Kc_mid to Kc_end (reaches Kc_end on the last day).
        return crop.kc_mid + (i - end_mid) / l_late * (crop.kc_end - crop.kc_mid)
    # Past the season: keeps Kc_end (a stated approximation of the skill).
    return crop.kc_end


def plan(plot: PlotInputs, forecast: Sequence[ForecastDay]) -> list[PlanDay]:
    """One PlanDay per forecast day, in order, simulating the soil water bucket day by day.

    The bucket: think of the root zone as a tank (a float field in a game's Update loop). Rain
    fills it, the crop drains it every day (ETc), and irrigation tops it up. It cannot hold more
    than TAW, and it cannot go below empty.

    Rather than tracking the level directly, FAO-56 tracks the depletion Dr: how many mm the
    bucket is BELOW full (Dr = 0 is full, Dr = TAW is empty). The level is TAW - Dr.
    RAW is the part of the bucket the crop can use without stress; the rule is to irrigate
    before the depletion would pass RAW.
    """
    crop = plot.crop

    # FAO-56 Ch. 8, Eq. 82: TAW = 1000 (theta_FC - theta_WP) Zr. The registry's soil value is
    # already the available water per metre of soil, so TAW = soil_mm_per_m x Zr (mm).
    taw = plot.soil_mm_per_m * crop.root_depth_m
    # FAO-56 Ch. 8, Eq. 83: RAW = p x TAW (mm).
    raw = crop.p * taw

    # Day 1 starts full (Dr = 0): the planner has no irrigation history (FAO-56 Eq. 87 note;
    # a stated assumption).
    dr = 0.0
    days: list[PlanDay] = []
    for fc in forecast:
        kc = kc_for(crop, plot.planting_date, fc.date)
        # FAO-56 Ch. 5, Eq. 56 (single crop coefficient): ETc = Kc x ET0 (mm for the day).
        etc = kc * fc.et0_mm

        # FAO-56 Ch. 8, Eq. 85 (daily water balance), applied in the skill's order.
        # 1. Rain first. Water above full is lost (runoff / deep percolation), so Dr floors at 0.
        dr_after_rain = max(0.0, dr - fc.rain_mm)

        # 2. Would today's crop use push the depletion past RAW? Strictly greater: exactly at
        #    the threshold does not irrigate. If so, irrigate in the morning to refill exactly
        #    the current depletion (rule I <= Dr: never more than fills the bucket), and the
        #    day ends with only today's ETc missing.
        if dr_after_rain + etc > raw:
            irrigation_mm = dr_after_rain
            dr_end = etc
        else:
            irrigation_mm = 0.0
            dr_end = dr_after_rain + etc

        # 3. FAO-56 Ch. 8, Eq. 86: the depletion cannot exceed TAW (the bucket cannot go below empty).
        dr_end = min(dr_end, taw)

        # From depth to volume and time (skill, section 6).
        litres = irrigation_mm * plot.area_m2  # 1 mm over 1 m2 = 1 litre
        # Each emitter waters a rectangle of row_spacing x emitter_spacing m2 (not FAO-56; the
        # course's worked example confirms it), so the area cancels out of the minutes.
        run_minutes = irrigation_mm * plot.row_spacing_m * plot.emitter_spacing_m / plot.emitter_flow_lph * 60

        days.append(
            PlanDay(
                date=fc.date,
                et0_mm=fc.et0_mm,
                kc=kc,
                irrigation_mm=irrigation_mm,
                litres=litres,
                run_minutes=run_minutes,
                stale=fc.stale,
                bucket_mm=taw - dr_end,
            )
        )
        dr = dr_end  # today's end is tomorrow's start
    return days
