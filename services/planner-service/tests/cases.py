"""The three hand-calculated cases, from the learner's own calculations (2026-11-18).

Each case is a fixed set of inputs and the expected result for each of the 7 days. The numbers
were calculated by hand in a spreadsheet, following the formulas in
.claude/skills/irrigation-calc-reference/SKILL.md, and re-checked independently. They are the
oracle for the engine: never change an expected value to make the engine pass. If the engine
and a case disagree, find out which one is wrong.
"""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Case:
    name: str
    crop_id: str
    soil_mm_per_m: float
    planting_date: date
    area_m2: float
    row_spacing_m: float
    emitter_spacing_m: float
    emitter_flow_lph: float
    start_date: date
    et0: list[float]
    rain: list[float]
    # One dict per day: kc, irrigation_mm, litres, run_minutes, bucket_mm.
    expected: list[dict[str, float]]


def _day(kc: float, irrigation_mm: float, litres: float, run_minutes: float, bucket_mm: float) -> dict[str, float]:
    return {
        "kc": kc,
        "irrigation_mm": irrigation_mm,
        "litres": litres,
        "run_minutes": run_minutes,
        "bucket_mm": bucket_mm,
    }


CASE_1 = Case(
    name="case 1: tomato in mid-season, sand, two irrigations",
    crop_id="tomato",
    soil_mm_per_m=83,
    planting_date=date(2026, 8, 1),
    area_m2=1000,
    row_spacing_m=1.5,
    emitter_spacing_m=0.4,
    emitter_flow_lph=2.0,
    start_date=date(2026, 10, 20),
    et0=[5.0, 5.5, 6.0, 6.0, 5.5, 5.0, 5.0],
    rain=[0, 0, 0, 0, 0, 0, 0],
    expected=[
        _day(1.15, 0, 0, 0, 52.35),
        _day(1.15, 0, 0, 0, 46.025),
        _day(1.15, 0, 0, 0, 39.125),
        _day(1.15, 18.975, 18975, 341.55, 51.2),
        _day(1.15, 0, 0, 0, 44.875),
        _day(1.15, 0, 0, 0, 39.125),
        _day(1.15, 18.975, 18975, 341.55, 52.35),
    ],
)

CASE_2 = Case(
    name="case 2: the same plot, 10 mm of rain on day 3 delays the irrigation",
    crop_id="tomato",
    soil_mm_per_m=83,
    planting_date=date(2026, 8, 1),
    area_m2=1000,
    row_spacing_m=1.5,
    emitter_spacing_m=0.4,
    emitter_flow_lph=2.0,
    start_date=date(2026, 10, 20),
    et0=[5.0, 5.5, 6.0, 6.0, 5.5, 5.0, 5.0],
    rain=[0, 0, 10.0, 0, 0, 0, 0],
    expected=[
        _day(1.15, 0, 0, 0, 52.35),
        _day(1.15, 0, 0, 0, 46.025),
        _day(1.15, 0, 0, 0, 49.125),
        _day(1.15, 0, 0, 0, 42.225),
        _day(1.15, 0, 0, 0, 35.9),
        _day(1.15, 22.2, 22200, 399.6, 52.35),
        _day(1.15, 0, 0, 0, 46.6),
    ],
)

CASE_3 = Case(
    name="case 3: bell pepper in the development stage, Kc changes every day",
    crop_id="bell-pepper",
    soil_mm_per_m=83,
    planting_date=date(2026, 9, 20),
    area_m2=400,
    row_spacing_m=1.2,
    emitter_spacing_m=0.3,
    emitter_flow_lph=2.0,
    start_date=date(2026, 10, 25),
    et0=[4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 4.0],
    rain=[0, 0, 0, 0, 0, 0, 0],
    expected=[
        _day(0.6771428571, 0, 0, 0, 38.79142857),
        _day(0.69, 0, 0, 0, 36.03142857),
        _day(0.7028571429, 0, 0, 0, 33.22),
        _day(0.7157142857, 0, 0, 0, 30.35714286),
        _day(0.7285714286, 11.14285714, 4457.142857, 120.3428571, 38.58571429),
        _day(0.7414285714, 0, 0, 0, 35.62),
        _day(0.7542857143, 0, 0, 0, 32.60285714),
    ],
)

CASES = [CASE_1, CASE_2, CASE_3]
