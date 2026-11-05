from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import DbConnection

router = APIRouter(prefix="/v1")


# Response models list the only fields the spec allows.
class Crop(BaseModel):
    id: str
    name: str


class Soil(BaseModel):
    id: str
    name: str
    available_water_mm_per_m: int


class Emitter(BaseModel):
    id: str
    name: str
    flow_lph: float


@router.get("/crops")
def list_crops(conn: DbConnection) -> list[Crop]:
    rows = conn.execute("SELECT id, name FROM crops ORDER BY id").fetchall()
    return [Crop.model_validate(dict(row)) for row in rows]


@router.get("/crops/{crop_id}")
def get_crop(crop_id: str, conn: DbConnection) -> Crop:
    row = conn.execute("SELECT id, name FROM crops WHERE id = ?", (crop_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Crop not found")
    return Crop.model_validate(dict(row))


@router.get("/soils")
def list_soils(conn: DbConnection) -> list[Soil]:
    rows = conn.execute(
        "SELECT id, name, available_water_mm_per_m FROM soils ORDER BY id"
    ).fetchall()
    return [Soil.model_validate(dict(row)) for row in rows]


@router.get("/soils/{soil_id}")
def get_soil(soil_id: str, conn: DbConnection) -> Soil:
    row = conn.execute(
        "SELECT id, name, available_water_mm_per_m FROM soils WHERE id = ?", (soil_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Soil not found")
    return Soil.model_validate(dict(row))


@router.get("/emitters")
def list_emitters(conn: DbConnection) -> list[Emitter]:
    rows = conn.execute("SELECT id, name, flow_lph FROM emitters ORDER BY id").fetchall()
    return [Emitter.model_validate(dict(row)) for row in rows]


@router.get("/emitters/{emitter_id}")
def get_emitter(emitter_id: str, conn: DbConnection) -> Emitter:
    row = conn.execute(
        "SELECT id, name, flow_lph FROM emitters WHERE id = ?", (emitter_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Emitter not found")
    return Emitter.model_validate(dict(row))
