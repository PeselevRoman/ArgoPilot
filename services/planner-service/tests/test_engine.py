"""Tests for engine.py, the pure irrigation calculation.

The formulas are in .claude/skills/irrigation-calc-reference/SKILL.md. The hand-calculated
cases in tests/cases.py are the learner's own oracle and are never edited to make a test pass.
"""

from datetime import date, timedelta
from pathlib import Path

import pytest

import engine
from crops import CROPS, Crop, get_crop
from engine import ForecastDay, PlanDay, PlotInputs, kc_for, plan
from tests.cases import CASES

PLANTING = date(2026, 1, 1)

# A synthetic crop for the bucket tests: Kc is 1 on every day, so ETc equals ET0.
# soil 100 mm/m x root depth 0.7 m gives TAW = 70.0 exactly in binary floats
# (100 * 0.7 rounds to exactly 70.0; checked), and p = 0.5 gives RAW = 35.0 exactly.
FLAT = Crop(kc_ini=1.0, kc_mid=1.0, kc_end=1.0, stage_days=(10, 10, 10, 10), root_depth_m=0.7, p=0.5)
TAW = 70.0


def flat_plot(**overrides) -> PlotInputs:
    values = dict(
        crop=FLAT,
        planting_date=PLANTING,
        area_m2=1000.0,
        row_spacing_m=1.5,
        emitter_spacing_m=0.4,
        emitter_flow_lph=2.0,
        soil_mm_per_m=100.0,
    )
    values.update(overrides)
    return PlotInputs(**values)


def forecast(et0: list[float], rain: list[float] | None = None, stale: list[bool] | None = None) -> list[ForecastDay]:
    rain = rain if rain is not None else [0.0] * len(et0)
    stale = stale if stale is not None else [False] * len(et0)
    return [
        ForecastDay(date=PLANTING + timedelta(days=n), et0_mm=e, rain_mm=r, stale=s)
        for n, (e, r, s) in enumerate(zip(et0, rain, stale))
    ]


def day_number(i: int) -> date:
    """The date of day number i (the planting day is day 1)."""
    return PLANTING + timedelta(days=i - 1)


# --- Kc -----------------------------------------------------------------------------------


def test_kc_on_the_planting_day_is_the_initial_value():
    tomato = get_crop("tomato")
    assert kc_for(tomato, PLANTING, PLANTING) == tomato.kc_ini


# Day index -> expected Kc, written out by hand from the skill's table.
# tomato: 30 / 40 / 45 / 30 days, Kc 0.6 / 1.15 / 0.80; total 145.
# bell-pepper: 30 / 35 / 40 / 20 days, Kc 0.6 / 1.05 / 0.90; total 125.
KC_BOUNDARIES = [
    ("tomato", 1, 0.6),
    ("tomato", 30, 0.6),
    ("tomato", 31, 0.6 + 1 / 40 * 0.55),  # 0.61375
    ("tomato", 70, 1.15),
    ("tomato", 71, 1.15),
    ("tomato", 115, 1.15),
    ("tomato", 116, 1.15 - 1 / 30 * 0.35),  # 1.138333...
    ("tomato", 145, 0.80),
    ("tomato", 146, 0.80),
    ("tomato", 645, 0.80),
    ("bell-pepper", 1, 0.6),
    ("bell-pepper", 30, 0.6),
    ("bell-pepper", 31, 0.6 + 1 / 35 * 0.45),  # 0.612857...
    ("bell-pepper", 65, 1.05),
    ("bell-pepper", 66, 1.05),
    ("bell-pepper", 105, 1.05),
    ("bell-pepper", 106, 1.05 - 1 / 20 * 0.15),  # 1.0425
    ("bell-pepper", 125, 0.90),
    ("bell-pepper", 126, 0.90),
    ("bell-pepper", 625, 0.90),
]


@pytest.mark.parametrize(("crop_id", "i", "expected"), KC_BOUNDARIES)
def test_kc_boundaries(crop_id, i, expected):
    assert kc_for(get_crop(crop_id), PLANTING, day_number(i)) == pytest.approx(expected, rel=1e-12)


def test_kc_is_linear_inside_development():
    # Tomato development is days 31..70 (40 days); day 50 is halfway (i - L_ini = 20 of 40).
    tomato = get_crop("tomato")
    assert kc_for(tomato, PLANTING, day_number(50)) == pytest.approx((tomato.kc_ini + tomato.kc_mid) / 2)


def test_planting_date_after_the_day_counts_as_day_one():
    tomato = get_crop("tomato")
    assert kc_for(tomato, date(2026, 6, 1), date(2026, 5, 1)) == tomato.kc_ini


def test_plot_past_its_season_keeps_kc_end():
    for crop in CROPS.values():
        assert kc_for(crop, PLANTING, PLANTING + timedelta(days=3000)) == crop.kc_end


# --- The bucket rule ----------------------------------------------------------------------


def test_assignment_example_irrigates_on_day_six():
    days = plan(flat_plot(), forecast([7.0] * 6))
    assert [d.bucket_mm for d in days[:5]] == [63.0, 56.0, 49.0, 42.0, 35.0]
    assert [d.irrigation_mm for d in days[:5]] == [0.0] * 5
    assert days[5].irrigation_mm == 35.0
    assert days[5].bucket_mm == TAW - 7.0


def test_exactly_at_the_threshold_does_not_irrigate():
    # Day 1: 0 + 35 = RAW exactly, not above it. Day 2: 35 + 1 > 35, so it irrigates.
    days = plan(flat_plot(), forecast([35.0, 1.0]))
    assert days[0].irrigation_mm == 0.0
    assert days[0].bucket_mm == 35.0
    assert days[1].irrigation_mm == 35.0


def test_bucket_starts_full_on_day_one():
    days = plan(flat_plot(), forecast([0.0]))
    assert days[0].bucket_mm == TAW
    assert days[0].irrigation_mm == 0.0


def test_start_depletion_default_is_the_full_bucket():
    assert plan(flat_plot(), forecast([1.0, 1.0])) == plan(flat_plot(), forecast([1.0, 1.0]), 0.0)


def test_start_depletion_above_raw_irrigates_on_day_one():
    # TAW 70, RAW 35. Start 60 mm down, so today's 1 mm pushes the depletion past RAW: refill 60 mm.
    day = plan(flat_plot(), forecast([1.0]), start_depletion_mm=60.0)[0]
    assert day.irrigation_mm == 60.0
    assert day.bucket_mm == TAW - 1.0


def test_start_depletion_below_raw_does_not_irrigate():
    day = plan(flat_plot(), forecast([1.0]), start_depletion_mm=10.0)[0]
    assert day.irrigation_mm == 0.0
    assert day.bucket_mm == TAW - 11.0


@pytest.mark.parametrize("start", [-0.5, TAW + 0.5])
def test_start_depletion_outside_zero_to_taw_is_refused(start):
    with pytest.raises(ValueError):
        plan(flat_plot(), forecast([1.0]), start_depletion_mm=start)


def test_rain_reduces_the_depletion():
    # Day 1 depletes 20; day 2 rain 5 then ETc 10: 20 - 5 + 10 = 25 depleted, level 45.
    days = plan(flat_plot(), forecast([20.0, 10.0], rain=[0.0, 5.0]))
    assert days[1].irrigation_mm == 0.0
    assert days[1].bucket_mm == 45.0


def test_rain_larger_than_the_depletion_does_not_overfill():
    # Day 1 depletes 10; day 2 rain 50 refills to full (depletion floors at 0), then ETc 3.
    days = plan(flat_plot(), forecast([10.0, 3.0, 0.0], rain=[0.0, 50.0, 100.0]))
    assert days[1].bucket_mm == TAW - 3.0
    assert days[2].bucket_mm == TAW
    assert all(d.bucket_mm <= TAW for d in days)


def test_irrigation_never_exceeds_the_depletion():
    et0 = [12.0, 9.0, 15.0, 30.0, 4.0, 22.0, 8.0, 40.0]
    rain = [0.0, 3.0, 0.0, 10.0, 0.0, 0.0, 25.0, 0.0]
    days = plan(flat_plot(), forecast(et0, rain))
    dr_start = 0.0
    for d, r in zip(days, rain):
        dr_after_rain = max(0.0, dr_start - r)
        assert d.irrigation_mm <= dr_after_rain
        dr_start = TAW - d.bucket_mm


def test_depletion_never_exceeds_taw():
    # Day 2's ETc (1000 mm) is far above the bucket: the depletion is capped at TAW.
    days = plan(flat_plot(), forecast([30.0, 1000.0]))
    assert days[1].irrigation_mm == 30.0
    assert days[1].bucket_mm == 0.0
    assert all(d.bucket_mm >= 0.0 for d in days)


def test_day_after_irrigation_starts_from_the_etc():
    days = plan(flat_plot(), forecast([20.0, 20.0, 6.0, 5.0]))
    # Day 2: 20 + 20 = 40 > 35, so it irrigates 20 and ends with Dr = ETc = 20.
    assert days[1].irrigation_mm == 20.0
    assert days[1].bucket_mm == TAW - 20.0
    # Day 3 starts from Dr = 20: 20 + 6 = 26, no irrigation.
    assert days[2].irrigation_mm == 0.0
    assert days[2].bucket_mm == TAW - 26.0


def test_stale_flag_is_copied_per_day():
    days = plan(flat_plot(), forecast([1.0, 1.0, 1.0], stale=[False, True, False]))
    assert [d.stale for d in days] == [False, True, False]


def test_plan_copies_date_and_et0_and_kc():
    fc = forecast([1.0, 2.0])
    days = plan(flat_plot(), fc)
    assert [d.date for d in days] == [f.date for f in fc]
    assert [d.et0_mm for d in days] == [1.0, 2.0]
    assert all(isinstance(d, PlanDay) and d.kc == 1.0 for d in days)


# --- From depth to litres and minutes -----------------------------------------------------


def test_litres_are_depth_times_area():
    days = plan(flat_plot(area_m2=250.0), forecast([7.0] * 6))
    assert days[5].litres == 35.0 * 250.0


def test_run_minutes_use_row_and_emitter_spacing_and_flow():
    # Day 1 depletes 10; day 2 irrigates 10 mm. 10 x 1.5 x 0.4 / 2.0 x 60 = 180 minutes.
    days = plan(flat_plot(row_spacing_m=1.5, emitter_spacing_m=0.4, emitter_flow_lph=2.0), forecast([10.0, 30.0]))
    assert days[1].irrigation_mm == 10.0
    assert days[1].run_minutes == pytest.approx(180.0)


def test_no_irrigation_means_zero_litres_and_minutes():
    days = plan(flat_plot(), forecast([5.0, 5.0]))
    for d in days:
        assert d.irrigation_mm == 0.0
        assert d.litres == 0.0
        assert d.run_minutes == 0.0


def test_area_does_not_change_the_run_minutes():
    small = plan(flat_plot(area_m2=500.0), forecast([7.0] * 6))[5]
    large = plan(flat_plot(area_m2=1000.0), forecast([7.0] * 6))[5]
    assert large.litres == 2 * small.litres
    assert large.run_minutes == small.run_minutes


# --- The learner's hand-calculated cases --------------------------------------------------


@pytest.mark.parametrize("case", CASES, ids=[c.name for c in CASES])
def test_hand_calculated_case(case):
    plot = PlotInputs(
        crop=get_crop(case.crop_id),
        planting_date=case.planting_date,
        area_m2=case.area_m2,
        row_spacing_m=case.row_spacing_m,
        emitter_spacing_m=case.emitter_spacing_m,
        emitter_flow_lph=case.emitter_flow_lph,
        soil_mm_per_m=case.soil_mm_per_m,
    )
    fc = [
        ForecastDay(date=case.start_date + timedelta(days=n), et0_mm=e, rain_mm=r, stale=False)
        for n, (e, r) in enumerate(zip(case.et0, case.rain))
    ]
    days = plan(plot, fc)
    assert len(days) == len(case.expected)
    for n, (got, want) in enumerate(zip(days, case.expected), start=1):
        for field, value in want.items():
            assert getattr(got, field) == pytest.approx(value, rel=0.005, abs=0.01), f"day {n}, {field}"


# --- Purity -------------------------------------------------------------------------------


def test_engine_does_no_io():
    source = Path(engine.__file__).read_text(encoding="utf-8")
    for forbidden in ("httpx", "open(", "datetime.now", "date.today"):
        assert forbidden not in source, forbidden
