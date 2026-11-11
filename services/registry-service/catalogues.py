from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from sqlalchemy import select

from db import Conn
from tables import crops, emitters, soils

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


def _list(conn: Conn, model, table):
    stmt = select(*(table.c[name] for name in model.model_fields)).order_by(table.c.id)
    return [model.model_validate(dict(row)) for row in conn.execute(stmt).mappings()]


def _get(conn: Conn, model, table, item_id: str, label: str):
    stmt = select(*(table.c[name] for name in model.model_fields)).where(table.c.id == item_id)
    row = conn.execute(stmt).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return model.model_validate(dict(row))


@router.get("/crops")
def list_crops(conn: Conn) -> list[Crop]:
    return _list(conn, Crop, crops)


@router.get("/crops/{crop_id}")
def get_crop(crop_id: str, conn: Conn) -> Crop:
    return _get(conn, Crop, crops, crop_id, "Crop")


@router.get("/soils")
def list_soils(conn: Conn) -> list[Soil]:
    return _list(conn, Soil, soils)


@router.get("/soils/{soil_id}")
def get_soil(soil_id: str, conn: Conn) -> Soil:
    return _get(conn, Soil, soils, soil_id, "Soil")


@router.get("/emitters")
def list_emitters(conn: Conn) -> list[Emitter]:
    return _list(conn, Emitter, emitters)


@router.get("/emitters/{emitter_id}")
def get_emitter(emitter_id: str, conn: Conn) -> Emitter:
    return _get(conn, Emitter, emitters, emitter_id, "Emitter")
