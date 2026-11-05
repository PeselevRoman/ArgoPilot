import sqlite3
import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, StringConstraints, model_validator

from db import DbConnection

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


def get_farm_or_404(conn: sqlite3.Connection, farm_id: str) -> Farm:
    row = conn.execute("SELECT id, name FROM farms WHERE id = ?", (farm_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Farm not found")
    return Farm.model_validate(dict(row))


def farm_has_plots(conn: sqlite3.Connection, farm_id: str) -> bool:
    row = conn.execute("SELECT 1 FROM plots WHERE farm_id = ? LIMIT 1", (farm_id,)).fetchone()
    return row is not None


@router.post("/farms", status_code=201)
def create_farm(body: FarmCreate, conn: DbConnection) -> Farm:
    farm = Farm(id=str(uuid.uuid4()), name=body.name)
    conn.execute("INSERT INTO farms (id, name) VALUES (?, ?)", (farm.id, farm.name))
    return farm


@router.get("/farms")
def list_farms(conn: DbConnection) -> list[Farm]:
    rows = conn.execute("SELECT id, name FROM farms ORDER BY id").fetchall()
    return [Farm.model_validate(dict(row)) for row in rows]


@router.get("/farms/{farm_id}")
def get_farm(farm_id: str, conn: DbConnection) -> Farm:
    return get_farm_or_404(conn, farm_id)


@router.patch("/farms/{farm_id}")
def update_farm(farm_id: str, body: FarmUpdate, conn: DbConnection) -> Farm:
    farm = get_farm_or_404(conn, farm_id)
    if "name" in body.model_fields_set:
        conn.execute("UPDATE farms SET name = ? WHERE id = ?", (body.name, farm_id))
        farm = Farm(id=farm_id, name=body.name)
    return farm


@router.delete("/farms/{farm_id}", status_code=204)
def delete_farm(farm_id: str, conn: DbConnection) -> Response:
    get_farm_or_404(conn, farm_id)
    if farm_has_plots(conn, farm_id):
        raise HTTPException(status_code=409, detail="Farm still has plots")
    try:
        conn.execute("DELETE FROM farms WHERE id = ?", (farm_id,))
    except sqlite3.IntegrityError:
        # A plot was added after the check above, and the database refused the delete.
        raise HTTPException(status_code=409, detail="Farm still has plots")
    return Response(status_code=204)
