import re
import sqlite3
import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Response
from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
    model_validator,
)

from db import DbConnection

router = APIRouter(prefix="/v1")


# Commas are allowed only as thousands separators, in groups of three: "1,000" or "1,234,567.5".
THOUSANDS_TEXT = re.compile(r"[+-]?[0-9]{1,3}(,[0-9]{3})+(\.[0-9]+)?")


def clean_number(value: object) -> object:
    # True and False are numbers in Python, so they must be refused explicitly.
    if isinstance(value, bool):
        raise ValueError("must be a number")
    if isinstance(value, str):
        text = value.strip()
        # Python reads "1_000" as 1000, which no client should send.
        if "_" in text:
            raise ValueError("must be a number")
        if "," in text:
            if not THOUSANDS_TEXT.fullmatch(text):
                raise ValueError("must be a number")
            return text.replace(",", "")
    return value


# Same rule as farm names: trim the ends, then reject a blank name.
NonBlankName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
# A string that holds a number, such as "1000", is converted to a number.
# Infinity is refused, since no plot can have an infinite area or coordinate.
PositiveNumber = Annotated[float, BeforeValidator(clean_number), Field(gt=0, allow_inf_nan=False)]
Latitude = Annotated[float, BeforeValidator(clean_number), Field(ge=-90, le=90, allow_inf_nan=False)]
Longitude = Annotated[float, BeforeValidator(clean_number), Field(ge=-180, le=180, allow_inf_nan=False)]

PLOT_COLUMNS = (
    "id, farm_id, name, area_m2, crop_id, planting_date, soil_id, "
    "row_spacing_m, emitter_spacing_m, emitter_id, lat, lon"
)


# Response model: only the fields the spec lists for a plot.
class Plot(BaseModel):
    id: str
    farm_id: str
    name: str
    area_m2: float
    crop_id: str
    planting_date: date
    soil_id: str
    row_spacing_m: float
    emitter_spacing_m: float
    emitter_id: str
    lat: float
    lon: float


class PlotCreate(BaseModel):
    # Extra fields are ignored by default, as the judgment log records.
    farm_id: str
    name: NonBlankName
    area_m2: PositiveNumber
    crop_id: str
    planting_date: date
    soil_id: str
    row_spacing_m: PositiveNumber
    emitter_spacing_m: PositiveNumber
    emitter_id: str
    lat: Latitude
    lon: Longitude

    @field_validator("planting_date")
    @classmethod
    def not_in_the_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("planting_date must not be in the future")
        return value


class PlotUpdate(BaseModel):
    # Only the fields sent in the body change. Each may be left out, but not null.
    farm_id: str | None = None
    name: NonBlankName | None = None
    area_m2: PositiveNumber | None = None
    crop_id: str | None = None
    planting_date: date | None = None
    soil_id: str | None = None
    row_spacing_m: PositiveNumber | None = None
    emitter_spacing_m: PositiveNumber | None = None
    emitter_id: str | None = None
    lat: Latitude | None = None
    lon: Longitude | None = None

    @model_validator(mode="after")
    def sent_fields_are_not_null(self) -> "PlotUpdate":
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


def get_plot_or_404(conn: sqlite3.Connection, plot_id: str) -> Plot:
    row = conn.execute(f"SELECT {PLOT_COLUMNS} FROM plots WHERE id = ?", (plot_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Plot not found")
    return Plot.model_validate(dict(row))


def check_references(conn: sqlite3.Connection, plot: PlotCreate) -> None:
    # A plot must point at a farm and at catalogue rows that exist.
    checks = [
        ("farms", plot.farm_id, "Unknown farm"),
        ("crops", plot.crop_id, "Unknown crop"),
        ("soils", plot.soil_id, "Unknown soil"),
        ("emitters", plot.emitter_id, "Unknown emitter"),
    ]
    for table, value, message in checks:
        # The table names come from the list above, never from the request.
        found = conn.execute(f"SELECT 1 FROM {table} WHERE id = ?", (value,)).fetchone()
        if found is None:
            raise HTTPException(status_code=422, detail=message)


def name_taken(conn: sqlite3.Connection, farm_id: str, name: str, ignore_id: str | None = None) -> bool:
    row = conn.execute(
        "SELECT id FROM plots WHERE farm_id = ? AND name = ? AND id != ? LIMIT 1",
        (farm_id, name, ignore_id or ""),
    ).fetchone()
    return row is not None


def plot_values(plot: Plot) -> dict:
    values = plot.model_dump()
    values["planting_date"] = plot.planting_date.isoformat()
    return values


@router.post("/plots", status_code=201)
def create_plot(body: PlotCreate, conn: DbConnection) -> Plot:
    check_references(conn, body)
    if name_taken(conn, body.farm_id, body.name):
        raise HTTPException(status_code=409, detail="Plot name already used on this farm")
    plot = Plot(id=str(uuid.uuid4()), **body.model_dump())
    try:
        conn.execute(
            f"INSERT INTO plots ({PLOT_COLUMNS}) VALUES "
            "(:id, :farm_id, :name, :area_m2, :crop_id, :planting_date, :soil_id, "
            ":row_spacing_m, :emitter_spacing_m, :emitter_id, :lat, :lon)",
            plot_values(plot),
        )
    except sqlite3.IntegrityError:
        # Another request may have taken the name, or deleted the farm, after the checks above.
        if name_taken(conn, body.farm_id, body.name):
            raise HTTPException(status_code=409, detail="Plot name already used on this farm")
        check_references(conn, body)
        raise
    return plot


@router.get("/plots")
def list_plots(conn: DbConnection, farm_id: str | None = None) -> list[Plot]:
    if farm_id is None:
        rows = conn.execute(f"SELECT {PLOT_COLUMNS} FROM plots ORDER BY id").fetchall()
    else:
        rows = conn.execute(
            f"SELECT {PLOT_COLUMNS} FROM plots WHERE farm_id = ? ORDER BY id", (farm_id,)
        ).fetchall()
    return [Plot.model_validate(dict(row)) for row in rows]


@router.get("/plots/{plot_id}")
def get_plot(plot_id: str, conn: DbConnection) -> Plot:
    return get_plot_or_404(conn, plot_id)


@router.patch("/plots/{plot_id}")
def update_plot(plot_id: str, body: PlotUpdate, conn: DbConnection) -> Plot:
    current = get_plot_or_404(conn, plot_id)
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        return current

    # Check the whole plot after the change, not just the new values.
    merged = {**current.model_dump(), **changes}
    try:
        updated = PlotCreate.model_validate(merged)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()[0]["msg"])
    check_references(conn, updated)
    if name_taken(conn, updated.farm_id, updated.name, ignore_id=plot_id):
        raise HTTPException(status_code=409, detail="Plot name already used on this farm")

    new = Plot(id=plot_id, **updated.model_dump())
    try:
        conn.execute(
            "UPDATE plots SET farm_id = :farm_id, name = :name, area_m2 = :area_m2, "
            "crop_id = :crop_id, planting_date = :planting_date, soil_id = :soil_id, "
            "row_spacing_m = :row_spacing_m, emitter_spacing_m = :emitter_spacing_m, "
            "emitter_id = :emitter_id, lat = :lat, lon = :lon WHERE id = :id",
            plot_values(new),
        )
    except sqlite3.IntegrityError:
        # Another request may have taken the name, or deleted the farm, after the checks above.
        if name_taken(conn, updated.farm_id, updated.name, ignore_id=plot_id):
            raise HTTPException(status_code=409, detail="Plot name already used on this farm")
        check_references(conn, updated)
        raise
    return new


@router.delete("/plots/{plot_id}", status_code=204)
def delete_plot(plot_id: str, conn: DbConnection) -> Response:
    get_plot_or_404(conn, plot_id)
    conn.execute("DELETE FROM plots WHERE id = ?", (plot_id,))
    return Response(status_code=204)
