import re
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

from sqlalchemy import Connection, Text, cast, delete, insert, select, update
from sqlalchemy.exc import IntegrityError

from db import Conn
from ids import parse_uuid
from tables import crops, emitters, farms, plots, soils

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
    plots.c.id, plots.c.farm_id, plots.c.name, plots.c.area_m2, plots.c.crop_id,
    plots.c.planting_date, plots.c.soil_id, plots.c.row_spacing_m,
    plots.c.emitter_spacing_m, plots.c.emitter_id, plots.c.lat, plots.c.lon,
)


# The list route returns ids as text, so it reads them as text and skips the UUID round trip.
# Postgres uuid::text is lowercase hyphenated, the same as the text SQLite stores.
LIST_COLUMNS = (
    cast(plots.c.id, Text).label("id"),
    cast(plots.c.farm_id, Text).label("farm_id"),
    *PLOT_COLUMNS[2:],
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


def plot_from_row(row) -> Plot:
    # The database gives UUID objects; the API shows them as text.
    values = dict(row)
    values["id"] = str(values["id"])
    values["farm_id"] = str(values["farm_id"])
    return Plot.model_validate(values)


def get_plot_or_404(conn: Connection, plot_id: str) -> Plot:
    # A malformed id cannot match any row, so it gets the same 404 as an unknown id.
    parsed = parse_uuid(plot_id)
    row = None
    if parsed is not None:
        row = conn.execute(select(*PLOT_COLUMNS).where(plots.c.id == parsed)).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Plot not found")
    return plot_from_row(row)


def check_references(conn: Connection, plot: PlotCreate) -> None:
    # A plot must point at a farm and at catalogue rows that exist.
    farm_id = parse_uuid(plot.farm_id)
    farm_found = False
    if farm_id is not None:
        farm_found = conn.execute(select(farms.c.id).where(farms.c.id == farm_id)).first() is not None
    if not farm_found:
        raise HTTPException(status_code=422, detail="Unknown farm")
    checks = [
        (crops, plot.crop_id, "Unknown crop"),
        (soils, plot.soil_id, "Unknown soil"),
        (emitters, plot.emitter_id, "Unknown emitter"),
    ]
    for table, value, message in checks:
        found = conn.execute(select(table.c.id).where(table.c.id == value)).first()
        if found is None:
            raise HTTPException(status_code=422, detail=message)


def name_taken(conn: Connection, farm_id: uuid.UUID, name: str, ignore_id: uuid.UUID | None = None) -> bool:
    stmt = select(plots.c.id).where(plots.c.farm_id == farm_id, plots.c.name == name)
    if ignore_id is not None:
        stmt = stmt.where(plots.c.id != ignore_id)
    return conn.execute(stmt.limit(1)).first() is not None


def body_farm_uuid(body: PlotCreate) -> uuid.UUID:
    # check_references has already refused a malformed farm_id, so this always parses.
    parsed = parse_uuid(body.farm_id)
    if parsed is None:
        raise HTTPException(status_code=422, detail="Unknown farm")
    return parsed


@router.post("/plots", status_code=201)
def create_plot(body: PlotCreate, conn: Conn) -> Plot:
    check_references(conn, body)
    farm_id = body_farm_uuid(body)
    if name_taken(conn, farm_id, body.name):
        raise HTTPException(status_code=409, detail="Plot name already used on this farm")
    new_id = uuid.uuid4()
    values = {**body.model_dump(), "id": new_id, "farm_id": farm_id}
    try:
        conn.execute(insert(plots).values(**values))
    except IntegrityError:
        # Another request may have taken the name, or deleted the farm, after the checks above.
        # PostgreSQL aborts the transaction after a failed statement, so roll back before
        # the re-check queries. The insert was the only write, so nothing is lost.
        conn.rollback()
        if name_taken(conn, farm_id, body.name):
            raise HTTPException(status_code=409, detail="Plot name already used on this farm")
        check_references(conn, body)
        raise
    return Plot(**{**body.model_dump(), "id": str(new_id), "farm_id": str(farm_id)})


@router.get("/plots")
def list_plots(conn: Conn, farm_id: str | None = None) -> list[Plot]:
    stmt = select(*LIST_COLUMNS).order_by(plots.c.id)
    if farm_id is not None:
        parsed = parse_uuid(farm_id)
        if parsed is None:
            return []
        stmt = stmt.where(plots.c.farm_id == parsed)
    keys = [column.name for column in stmt.selected_columns]
    return [Plot.model_validate(dict(zip(keys, row))) for row in conn.execute(stmt)]


@router.get("/plots/{plot_id}")
def get_plot(plot_id: str, conn: Conn) -> Plot:
    return get_plot_or_404(conn, plot_id)


@router.patch("/plots/{plot_id}")
def update_plot(plot_id: str, body: PlotUpdate, conn: Conn) -> Plot:
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
    farm_id = body_farm_uuid(updated)
    plot_uuid = uuid.UUID(current.id)
    if name_taken(conn, farm_id, updated.name, ignore_id=plot_uuid):
        raise HTTPException(status_code=409, detail="Plot name already used on this farm")

    values = {**updated.model_dump(), "farm_id": farm_id}
    try:
        conn.execute(update(plots).where(plots.c.id == plot_uuid).values(**values))
    except IntegrityError:
        # Another request may have taken the name, or deleted the farm, after the checks above.
        # Roll back first: PostgreSQL refuses further queries in an aborted transaction.
        conn.rollback()
        if name_taken(conn, farm_id, updated.name, ignore_id=plot_uuid):
            raise HTTPException(status_code=409, detail="Plot name already used on this farm")
        check_references(conn, updated)
        raise
    return Plot(**{**updated.model_dump(), "id": current.id, "farm_id": str(farm_id)})


@router.delete("/plots/{plot_id}", status_code=204)
def delete_plot(plot_id: str, conn: Conn) -> Response:
    plot = get_plot_or_404(conn, plot_id)
    conn.execute(delete(plots).where(plots.c.id == uuid.UUID(plot.id)))
    return Response(status_code=204)
