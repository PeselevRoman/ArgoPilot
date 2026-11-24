"""Write the numbers for the P2 demo's stand-in, from the real engine.

Run from services/planner-service:
    uv run python demo_numbers.py            # write scripts/demo/plan_numbers.json
    uv run python demo_numbers.py --check    # exit 1 if the saved file is out of date

The four plots are read from tasks/seed_registry.sh (the seed script builds a temporary database,
and this script reads it), so no plot value is copied by hand. The engine (engine.py) makes every
number. This script only picks the scenarios and rounds the output the same way the endpoint does.

Scenarios:
- "water": each plot planted in mid-season, and started partly dry by a stated share of its RAW
  (START_SHARE_OF_RAW). Both are our choices for the demo, not from the seed or the planner.
- "stale": the same as "water", with the forecast marked stale.
- "full": the seed's own planting dates. Those plots are past their season, so the plan is low
  and, with the bucket starting full, has no irrigation (see TODO.md, item 2).
"""

import json
import sqlite3
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

from crops import get_crop
from engine import ForecastDay, PlotInputs, plan

SERVICE_DIR = Path(__file__).resolve().parent
REPO_DIR = SERVICE_DIR.parent.parent
SEED_SCRIPT = REPO_DIR / "tasks" / "seed_registry.sh"
OUTPUT = REPO_DIR / "scripts" / "demo" / "plan_numbers.json"

FORECAST_START = date(2026, 11, 27)
# Real ET0 (FAO-56 Penman-Monteith, mm per day) for a hot week: 12 to 18 July 2025, the hottest
# 7-day window (highest mean) in Open-Meteo's archive for July and August 2025 at the seed's
# coordinates (31.25, 34.79; Open-Meteo snaps them to its grid, 31.2478, 34.8214). Source:
# https://archive-api.open-meteo.com/v1/archive?latitude=31.25&longitude=34.79&start_date=2025-07-01&end_date=2025-08-31&daily=et0_fao_evapotranspiration&timezone=auto
# The values are placed on the demo's dates (FORECAST_START), so the crop stages stay as planned.
# Rain is 0 on every day.
ET0_MM = [6.95, 6.49, 6.49, 7.13, 8.28, 8.82, 7.66]

# Mid-season planting dates for the "water" scenario, by the seed's plot id.
MID_SEASON_PLANTING = {
    "c8f3d1b0-4d2e-5a1b-8b22-1d6e3f702002": date(2026, 9, 20),  # North block, tomato
    "d9a4e2c1-5e3f-4b6a-9c33-2e7f4a803003": date(2026, 10, 1),  # East block, bell pepper
    "e0b5f3d2-6f40-4c7b-8d44-3f8a5b914004": date(2026, 9, 20),  # West block, tomato
    "f1c6a4e3-7051-4d8c-9e55-4a9b6c025005": date(2026, 10, 1),  # Greenhouse, bell pepper
}

# The starting dryness for the "water" scenario, as a share of each plot's RAW (the water the crop
# can use before stress). This is a demo assumption, read as a grower's field check, not a value
# the planner receives: the planner has no soil-moisture input (services/planner-service/TODO.md,
# item 1). The shares are chosen to show different cases, and the engine does the rest:
# - North block (loam): dry, so it irrigates on day 1.
# - West block (sand, holds least): dry, and it irrigates most often.
# - East block (clay loam, holds most): wet, so no irrigation this week.
# - Greenhouse (loam, small area): half-dry, so it irrigates a day or two later.
START_SHARE_OF_RAW = {
    "c8f3d1b0-4d2e-5a1b-8b22-1d6e3f702002": 0.9,  # North block
    "d9a4e2c1-5e3f-4b6a-9c33-2e7f4a803003": 0.3,  # East block
    "e0b5f3d2-6f40-4c7b-8d44-3f8a5b914004": 0.9,  # West block
    "f1c6a4e3-7051-4d8c-9e55-4a9b6c025005": 0.6,  # Greenhouse
}


def raw_mm(plot: dict) -> float:
    """RAW = p x TAW, with TAW = soil mm/m x root depth (FAO-56 Eq. 82 and 83), from the seed values."""
    crop = get_crop(plot["crop_id"])
    return crop.p * plot["available_water_mm_per_m"] * crop.root_depth_m


def read_seed_plots() -> list[dict]:
    """The plots of the seed, with their soil and emitter values, from a temporary database."""
    with tempfile.TemporaryDirectory() as folder:
        db = Path(folder) / "registry.db"
        subprocess.run(["bash", str(SEED_SCRIPT), str(db)], check=True, capture_output=True)
        with sqlite3.connect(db) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT p.id, p.name, p.crop_id, p.area_m2, p.planting_date, p.row_spacing_m,
                       p.emitter_spacing_m, s.available_water_mm_per_m, e.flow_lph
                FROM plots p
                JOIN soils s ON s.id = p.soil_id
                JOIN emitters e ON e.id = p.emitter_id
                ORDER BY p.name
                """
            ).fetchall()
    return [dict(row) for row in rows]


def scenario_days(plot: dict, planting: date, stale: bool, start_depletion_mm: float = 0.0) -> list[dict]:
    """Run the engine for one plot and round the answer the same way the endpoint does."""
    inputs = PlotInputs(
        crop=get_crop(plot["crop_id"]),
        planting_date=planting,
        area_m2=plot["area_m2"],
        row_spacing_m=plot["row_spacing_m"],
        emitter_spacing_m=plot["emitter_spacing_m"],
        emitter_flow_lph=plot["flow_lph"],
        soil_mm_per_m=plot["available_water_mm_per_m"],
    )
    forecast = [
        ForecastDay(FORECAST_START + timedelta(days=i), et0, 0.0, stale) for i, et0 in enumerate(ET0_MM)
    ]
    return [
        {
            "date": day.date.isoformat(),
            "et0_mm": round(day.et0_mm, 2),
            "kc": round(day.kc, 3),
            "litres": round(day.litres, 2),
            "run_minutes": round(day.run_minutes, 2),
            "stale": day.stale,
            "bucket_mm": round(day.bucket_mm, 2),
        }
        for day in plan(inputs, forecast, start_depletion_mm)
    ]


def build() -> dict:
    plots = read_seed_plots()
    scenarios: dict[str, dict] = {"water": {}, "stale": {}, "full": {}}
    for plot in plots:
        mid = MID_SEASON_PLANTING[plot["id"]]
        seed_planting = date.fromisoformat(plot["planting_date"])
        share = START_SHARE_OF_RAW[plot["id"]]
        start_mm = round(share * raw_mm(plot), 2)
        meta = {"name": plot["name"], "crop_id": plot["crop_id"], "area_m2": plot["area_m2"]}
        scenarios["water"][plot["id"]] = {
            **meta,
            "planting_date": mid.isoformat(),
            "start_depletion_mm": start_mm,
            "start_share_of_raw": share,
            "days": scenario_days(plot, mid, stale=False, start_depletion_mm=start_mm),
        }
        scenarios["stale"][plot["id"]] = {
            **meta,
            "planting_date": mid.isoformat(),
            "start_depletion_mm": start_mm,
            "start_share_of_raw": share,
            "days": scenario_days(plot, mid, stale=True, start_depletion_mm=start_mm),
        }
        # The seed's own plots start full (the planner's real answer today): start depletion 0.
        scenarios["full"][plot["id"]] = {
            **meta,
            "planting_date": seed_planting.isoformat(),
            "start_depletion_mm": 0.0,
            "days": scenario_days(plot, seed_planting, stale=False),
        }
    return {
        "about": "Written by services/planner-service/demo_numbers.py from the real engine. Do not edit by hand.",
        "forecast_start": FORECAST_START.isoformat(),
        "et0_mm": ET0_MM,
        "scenarios": scenarios,
    }


def render(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    text = render(build())
    if "--check" in argv:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != text:
            print(f"{OUTPUT} is out of date. Run: uv run python demo_numbers.py")
            return 1
        print(f"{OUTPUT} is up to date.")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(text, encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
