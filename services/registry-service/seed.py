"""Set up a new registry database: create the tables and load the sample data.

Usage, from this folder:
    uv run python seed.py

It works on the database in DATABASE_URL (SQLite or PostgreSQL) and does the
same as seed_registry.sh, which only handles SQLite. It never deletes anything:
if any of the tables already exists, it stops and changes nothing.
"""

import datetime
import sys
import uuid
from pathlib import Path

from sqlalchemy import Connection, Engine, inspect

import db
import tables

SERVICE_DIR = Path(__file__).parent

CROPS = [
    {"id": "tomato", "name": "Tomato"},
    {"id": "bell-pepper", "name": "Bell pepper"},
]

SOILS = [
    {"id": "sand", "name": "Sand", "available_water_mm_per_m": 83},
    {"id": "loam", "name": "Loam", "available_water_mm_per_m": 175},
    {"id": "clay-loam", "name": "Clay loam", "available_water_mm_per_m": 200},
]

EMITTERS = [
    {"id": "dripnet-pc-0.6", "name": "DripNet PC", "flow_lph": 0.6},
    {"id": "dripnet-pc-1.0", "name": "DripNet PC", "flow_lph": 1.0},
    {"id": "dripnet-pc-1.6", "name": "DripNet PC", "flow_lph": 1.6},
    {"id": "dripnet-pc-2.0", "name": "DripNet PC", "flow_lph": 2.0},
]

DEMO_FARM = uuid.UUID("b7e2c0a0-3c1d-4f0a-9a11-0c5d2e6f1001")
EAST_FARM = uuid.UUID("a9c1e4b2-6f70-4d8e-a144-3f8b5c904004")

FARMS = [
    {"id": DEMO_FARM, "name": "Demo cooperative"},
    {"id": EAST_FARM, "name": "East farm"},
]

PLOTS = [
    {
        "id": uuid.UUID("c8f3d1b0-4d2e-5a1b-8b22-1d6e3f702002"), "farm_id": DEMO_FARM,
        "name": "North block", "area_m2": 1000, "crop_id": "tomato",
        "planting_date": datetime.date(2026, 3, 1), "soil_id": "loam",
        "row_spacing_m": 1.5, "emitter_spacing_m": 0.4, "emitter_id": "dripnet-pc-1.0",
        "lat": 31.25, "lon": 34.79,
    },
    {
        "id": uuid.UUID("d9a4e2c1-5e3f-4b6a-9c33-2e7f4a803003"), "farm_id": DEMO_FARM,
        "name": "East block", "area_m2": 800, "crop_id": "bell-pepper",
        "planting_date": datetime.date(2026, 4, 12), "soil_id": "clay-loam",
        "row_spacing_m": 1.5, "emitter_spacing_m": 0.4, "emitter_id": "dripnet-pc-1.6",
        "lat": 31.26, "lon": 34.80,
    },
    {
        "id": uuid.UUID("e0b5f3d2-6f40-4c7b-8d44-3f8a5b914004"), "farm_id": EAST_FARM,
        "name": "West block", "area_m2": 1500, "crop_id": "tomato",
        "planting_date": datetime.date(2026, 2, 15), "soil_id": "sand",
        "row_spacing_m": 1.5, "emitter_spacing_m": 0.4, "emitter_id": "dripnet-pc-0.6",
        "lat": 31.40, "lon": 34.60,
    },
    {
        "id": uuid.UUID("f1c6a4e3-7051-4d8c-9e55-4a9b6c025005"), "farm_id": EAST_FARM,
        "name": "Greenhouse", "area_m2": 400, "crop_id": "bell-pepper",
        "planting_date": datetime.date(2026, 5, 1), "soil_id": "loam",
        "row_spacing_m": 1.2, "emitter_spacing_m": 0.3, "emitter_id": "dripnet-pc-2.0",
        "lat": 31.41, "lon": 34.61,
    },
]


class SeedError(RuntimeError):
    """The database cannot be seeded, for example because it already has tables."""


def _run_schema(conn: Connection) -> None:
    schema = "schema.sql" if conn.dialect.name == "sqlite" else "schema.postgres.sql"
    statements = [s.strip() for s in (SERVICE_DIR / schema).read_text().split(";") if s.strip()]
    for statement in statements:
        conn.exec_driver_sql(statement)


def create_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        _run_schema(conn)


def seed(engine: Engine) -> None:
    # Check first, before any write: an existing database must stay untouched.
    existing = set(inspect(engine).get_table_names()) & set(tables.metadata.tables)
    if existing:
        raise SeedError(
            f"The database already has tables ({', '.join(sorted(existing))}). "
            "Nothing was changed. Use an empty database."
        )
    # One transaction: if an insert fails, the tables are not left half-built.
    with engine.begin() as conn:
        if conn.dialect.name == "sqlite":
            # Python's SQLite driver does not open a transaction before CREATE TABLE, so a
            # failed insert would leave the tables behind. Open one by hand.
            conn.exec_driver_sql("BEGIN")
        _run_schema(conn)
        conn.execute(tables.crops.insert(), CROPS)
        conn.execute(tables.soils.insert(), SOILS)
        conn.execute(tables.emitters.insert(), EMITTERS)
        conn.execute(tables.farms.insert(), FARMS)
        conn.execute(tables.plots.insert(), PLOTS)


def main() -> int:
    try:
        engine = db.get_engine()
        seed(engine)
    except RuntimeError as error:  # SeedError, and a missing or invalid DATABASE_URL
        print(error, file=sys.stderr)
        return 1
    print(f"Seeded {engine.url.database}: 2 farms, 4 plots, 2 crops, 3 soils, 4 emitters.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
