from datetime import date
from uuid import UUID

import pytest
from sqlalchemy import create_engine, insert, select, text

from ids import parse_uuid
from tables import crops, emitters, farms, metadata, plots, soils

FARM_ID = "b7e2c0a0-3c1d-4f0a-9a11-0c5d2e6f1001"


@pytest.fixture
def engine():
    engine = create_engine("sqlite://")
    metadata.create_all(engine)
    return engine


def test_parse_uuid_accepts_any_uuid_form():
    expected = UUID(FARM_ID)
    assert parse_uuid(FARM_ID) == expected
    assert parse_uuid(FARM_ID.upper()) == expected
    assert parse_uuid(FARM_ID.replace("-", "")) == expected
    assert parse_uuid("{" + FARM_ID + "}") == expected


@pytest.mark.parametrize("value", ["", "garbage", "b7e2c0a0", "some-id"])
def test_parse_uuid_returns_none_for_malformed_text(value):
    assert parse_uuid(value) is None


def test_uuid_is_stored_as_hyphenated_text_on_sqlite(engine):
    with engine.begin() as conn:
        conn.execute(insert(farms).values(id=UUID(FARM_ID), name="Farm"))
        stored = conn.execute(text("SELECT id FROM farms")).scalar_one()
    assert stored == FARM_ID


def test_existing_hyphenated_row_can_be_read_and_filtered(engine):
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO farms (id, name) VALUES (:id, 'Farm')"), {"id": FARM_ID}
        )
        row = conn.execute(select(farms).where(farms.c.id == UUID(FARM_ID))).one()
    assert row.id == UUID(FARM_ID)
    assert isinstance(row.id, UUID)


def test_date_round_trips_as_iso_text(engine):
    plot_id = UUID("c1a2b3c4-0000-4000-8000-000000000001")
    with engine.begin() as conn:
        conn.execute(insert(farms).values(id=UUID(FARM_ID), name="Farm"))
        conn.execute(insert(crops).values(id="c1", name="Crop"))
        conn.execute(insert(soils).values(id="s1", name="Soil", available_water_mm_per_m=100))
        conn.execute(insert(emitters).values(id="e1", name="Emitter", flow_lph=2.0))
        conn.execute(
            insert(plots).values(
                id=plot_id, farm_id=UUID(FARM_ID), name="Plot", area_m2=10.0,
                crop_id="c1", planting_date=date(2026, 3, 1), soil_id="s1",
                row_spacing_m=1.0, emitter_spacing_m=0.5, emitter_id="e1",
                lat=1.0, lon=2.0,
            )
        )
        stored = conn.execute(text("SELECT planting_date FROM plots")).scalar_one()
        read = conn.execute(select(plots.c.planting_date)).scalar_one()
    assert stored == "2026-03-01"
    assert read == date(2026, 3, 1)
