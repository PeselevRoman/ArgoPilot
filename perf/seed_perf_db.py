"""Build the performance database: 100 farms and 10,000 plots.

The target is a SQLite file path or a database URL. A SQLite file is deleted and
rewritten. A PostgreSQL database is rebuilt (its tables are dropped), and only
if its name contains 'perf'.

Usage, from the repository root, with the service's own Python:
    services/registry-service/.venv/bin/python perf/seed_perf_db.py perf/perf.db
    services/registry-service/.venv/bin/python perf/seed_perf_db.py "$PERF_DATABASE_URL"
"""

import datetime
import os
import random
import sys
import uuid
from pathlib import Path

SERVICE = Path(__file__).resolve().parent.parent / "services" / "registry-service"
sys.path.insert(0, str(SERVICE))

import db  # noqa: E402
import seed  # noqa: E402
import tables  # noqa: E402
from perf_target import check_rebuildable, safe, to_url  # noqa: E402

FARMS = 100
PLOTS = 10_000
SEED = 42  # A fixed seed, so every run builds the same data.


def random_uuid(rng: random.Random) -> uuid.UUID:
    return uuid.UUID(int=rng.getrandbits(128), version=4)


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: python perf/seed_perf_db.py PATH_OR_DATABASE_URL")
    url = to_url(sys.argv[1])
    check_rebuildable(url)  # before anything is deleted or dropped

    os.environ["DATABASE_URL"] = url
    engine = db.get_engine()
    if engine.dialect.name == "sqlite":
        Path(engine.url.database).unlink(missing_ok=True)
    else:
        with engine.begin() as conn:
            conn.exec_driver_sql("DROP TABLE IF EXISTS plots, farms, crops, soils, emitters CASCADE")

    rng = random.Random(SEED)
    farm_ids = [random_uuid(rng) for _ in range(FARMS)]
    farms = [{"id": farm_id, "name": f"Farm {number}"} for number, farm_id in enumerate(farm_ids, start=1)]

    plots = []
    for number in range(PLOTS):
        # Plot names only need to be unique within their farm.
        plots.append({
            "id": random_uuid(rng),
            "farm_id": farm_ids[number % FARMS],
            "name": f"Plot {number // FARMS + 1}",
            "area_m2": round(rng.uniform(200, 5000), 1),
            "crop_id": rng.choice(seed.CROPS)["id"],
            "planting_date": datetime.date(2026, rng.randint(1, 9), rng.randint(1, 28)),
            "soil_id": rng.choice(seed.SOILS)["id"],
            "row_spacing_m": 1.5,
            "emitter_spacing_m": 0.4,
            "emitter_id": rng.choice(seed.EMITTERS)["id"],
            "lat": round(rng.uniform(-60, 60), 4),
            "lon": round(rng.uniform(-170, 170), 4),
        })

    seed.create_schema(engine)
    with engine.begin() as conn:
        conn.execute(tables.crops.insert(), seed.CROPS)
        conn.execute(tables.soils.insert(), seed.SOILS)
        conn.execute(tables.emitters.insert(), seed.EMITTERS)
        conn.execute(tables.farms.insert(), farms)
        conn.execute(tables.plots.insert(), plots)
    print(f"Wrote {safe(url)}: {FARMS} farms, {PLOTS} plots")


if __name__ == "__main__":
    main()
