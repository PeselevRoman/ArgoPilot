"""Build the performance database: 100 farms and 10,000 plots.

Usage, from the repository root:
    python3 perf/seed_perf_db.py perf/perf.db
"""

import random
import sqlite3
import sys
import uuid
from pathlib import Path

SERVICE = Path(__file__).resolve().parent.parent / "services" / "registry-service"
SCHEMA = SERVICE / "schema.sql"

FARMS = 100
PLOTS = 10_000
SEED = 42  # A fixed seed, so every run builds the same data.

CROPS = [("tomato", "Tomato"), ("bell-pepper", "Bell pepper")]
SOILS = [("sand", "Sand", 83), ("loam", "Loam", 175), ("clay-loam", "Clay loam", 200)]
EMITTERS = [
    ("dripnet-pc-0.6", "DripNet PC", 0.6),
    ("dripnet-pc-1.0", "DripNet PC", 1.0),
    ("dripnet-pc-1.6", "DripNet PC", 1.6),
    ("dripnet-pc-2.0", "DripNet PC", 2.0),
]


def random_uuid(rng: random.Random) -> str:
    return str(uuid.UUID(int=rng.getrandbits(128), version=4))


def main() -> None:
    target = Path(sys.argv[1])
    target.unlink(missing_ok=True)
    rng = random.Random(SEED)

    conn = sqlite3.connect(target)
    conn.executescript(SCHEMA.read_text())
    conn.executemany("INSERT INTO crops (id, name) VALUES (?, ?)", CROPS)
    conn.executemany("INSERT INTO soils (id, name, available_water_mm_per_m) VALUES (?, ?, ?)", SOILS)
    conn.executemany("INSERT INTO emitters (id, name, flow_lph) VALUES (?, ?, ?)", EMITTERS)

    farm_ids = [random_uuid(rng) for _ in range(FARMS)]
    conn.executemany(
        "INSERT INTO farms (id, name) VALUES (?, ?)",
        [(farm_id, f"Farm {number}") for number, farm_id in enumerate(farm_ids, start=1)],
    )

    plots = []
    for number in range(PLOTS):
        farm_id = farm_ids[number % FARMS]
        # Plot names only need to be unique within their farm.
        plots.append((
            random_uuid(rng),
            farm_id,
            f"Plot {number // FARMS + 1}",
            round(rng.uniform(200, 5000), 1),
            rng.choice(CROPS)[0],
            f"2026-{rng.randint(1, 9):02d}-{rng.randint(1, 28):02d}",
            rng.choice(SOILS)[0],
            1.5,
            0.4,
            rng.choice(EMITTERS)[0],
            round(rng.uniform(-60, 60), 4),
            round(rng.uniform(-170, 170), 4),
        ))
    conn.executemany(
        "INSERT INTO plots (id, farm_id, name, area_m2, crop_id, planting_date, soil_id, "
        "row_spacing_m, emitter_spacing_m, emitter_id, lat, lon) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        plots,
    )
    conn.commit()
    conn.close()
    print(f"Wrote {target}: {FARMS} farms, {PLOTS} plots")


if __name__ == "__main__":
    main()
