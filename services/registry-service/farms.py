import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, StringConstraints, model_validator

from sqlalchemy import Connection, delete, exists, insert, select, update
from sqlalchemy.exc import IntegrityError

from db import Conn
from ids import parse_uuid
from tables import farms, plots

router = APIRouter(prefix="/v1")

# Leading and trailing spaces are removed first. A name that is blank after that is rejected.
NonBlankName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


# Response model: only the fields the spec lists for a farm.
class Farm(BaseModel):
    id: str
    name: str


class FarmCreate(BaseModel):
    # Extra fields are ignored by default, as the judgment log records.
    name: NonBlankName


class FarmUpdate(BaseModel):
    # Only the fields sent in the body change. name may be left out, but not null.
    name: NonBlankName | None = None

    @model_validator(mode="after")
    def name_is_not_null_when_sent(self) -> "FarmUpdate":
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name must be a non-empty string")
        return self


def get_farm_or_404(conn: Connection, farm_id: str) -> Farm:
    # A malformed id cannot match any row, so it gets the same 404 as an unknown id.
    parsed = parse_uuid(farm_id)
    row = None
    if parsed is not None:
        stmt = select(farms.c.id, farms.c.name).where(farms.c.id == parsed)
        row = conn.execute(stmt).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Farm not found")
    return Farm(id=str(row["id"]), name=row["name"])


def farm_has_plots(conn: Connection, farm_id: uuid.UUID) -> bool:
    return bool(conn.scalar(select(exists().where(plots.c.farm_id == farm_id))))


@router.post("/farms", status_code=201)
def create_farm(body: FarmCreate, conn: Conn) -> Farm:
    new_id = uuid.uuid4()
    conn.execute(insert(farms).values(id=new_id, name=body.name))
    return Farm(id=str(new_id), name=body.name)


@router.get("/farms")
def list_farms(conn: Conn) -> list[Farm]:
    stmt = select(farms.c.id, farms.c.name).order_by(farms.c.id)
    return [
        Farm(id=str(row["id"]), name=row["name"]) for row in conn.execute(stmt).mappings()
    ]


@router.get("/farms/{farm_id}")
def get_farm(farm_id: str, conn: Conn) -> Farm:
    return get_farm_or_404(conn, farm_id)


@router.patch("/farms/{farm_id}")
def update_farm(farm_id: str, body: FarmUpdate, conn: Conn) -> Farm:
    farm = get_farm_or_404(conn, farm_id)
    if "name" in body.model_fields_set:
        conn.execute(update(farms).where(farms.c.id == uuid.UUID(farm.id)).values(name=body.name))
        farm = Farm(id=farm.id, name=body.name)
    return farm


@router.delete("/farms/{farm_id}", status_code=204)
def delete_farm(farm_id: str, conn: Conn) -> Response:
    farm = get_farm_or_404(conn, farm_id)
    parsed = uuid.UUID(farm.id)
    if farm_has_plots(conn, parsed):
        raise HTTPException(status_code=409, detail="Farm still has plots")
    try:
        conn.execute(delete(farms).where(farms.c.id == parsed))
    except IntegrityError:
        # A plot was added after the check above, and the database refused the delete.
        # PostgreSQL aborts the whole transaction after a failed statement, so roll back
        # before raising. The delete is the only write, so nothing is lost.
        conn.rollback()
        raise HTTPException(status_code=409, detail="Farm still has plots")
    return Response(status_code=204)
