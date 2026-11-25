"""Checks for the demo's numbers (demo_numbers.py, written to scripts/demo/plan_numbers.json).

They run the real engine, so they fail if the saved file is out of date, or if a day's water
balance does not add up.
"""

import json

import pytest

import demo_numbers

SCENARIOS = ("water", "stale", "full")
# Water balance (FAO-56 Eq. 85, no rain): the bucket falls by ETc each day and rises by the
# irrigation. The file rounds to 2 decimals, so each number can be off by 0.005 mm.
TOLERANCE_MM = 0.02


@pytest.fixture(scope="module")
def numbers() -> dict:
    return json.loads(demo_numbers.OUTPUT.read_text(encoding="utf-8"))


def test_the_saved_file_is_the_engine_output():
    assert demo_numbers.OUTPUT.read_text(encoding="utf-8") == demo_numbers.render(demo_numbers.build())


def test_every_scenario_has_the_four_seed_plots(numbers):
    seed_ids = {plot["id"] for plot in demo_numbers.read_seed_plots()}
    assert len(seed_ids) == 4
    for scenario in SCENARIOS:
        assert set(numbers["scenarios"][scenario]) == seed_ids


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_each_day_balances_the_bucket(numbers, scenario):
    # bucket(today) = bucket(yesterday) - ETc + irrigation (in mm), so
    # irrigation = bucket change + ETc. The irrigation in mm is litres / area.
    for plot in numbers["scenarios"][scenario].values():
        days = plot["days"]
        for previous, today in zip(days, days[1:]):
            etc = today["kc"] * today["et0_mm"]
            irrigation_mm = today["litres"] / plot["area_m2"]
            change = today["bucket_mm"] - previous["bucket_mm"]
            assert change + etc == pytest.approx(irrigation_mm, abs=TOLERANCE_MM), (plot["name"], today["date"])


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_no_day_is_above_full_or_below_empty(numbers, scenario):
    # The bucket holds at most TAW (soil mm/m x root depth) and never less than 0. The largest TAW
    # in the seed is clay loam under tomato: 200 x 0.7 = 140 mm.
    for plot in numbers["scenarios"][scenario].values():
        for day in plot["days"]:
            assert 0 <= day["bucket_mm"] <= 140
