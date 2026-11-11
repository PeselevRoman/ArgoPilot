import uuid

from sqlalchemy import (
    Column, Date, Double, ForeignKey, Integer, MetaData, Table, Text,
    UniqueConstraint,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import TypeDecorator


class UuidId(TypeDecorator):
    """Python uuid.UUID in code; native uuid on Postgres, hyphenated TEXT on SQLite.

    SQLAlchemy's built-in Uuid is not used: on SQLite it stores 32 hex characters
    without hyphens, which would not match the existing hyphenated rows.
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.UUID(as_uuid=True))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value if isinstance(value, uuid.UUID) else uuid.UUID(value)


metadata = MetaData()

farms = Table(
    "farms", metadata,
    Column("id", UuidId, primary_key=True),
    Column("name", Text, nullable=False),
)

crops = Table(
    "crops", metadata,
    Column("id", Text, primary_key=True),
    Column("name", Text, nullable=False),
)

soils = Table(
    "soils", metadata,
    Column("id", Text, primary_key=True),
    Column("name", Text, nullable=False),
    Column("available_water_mm_per_m", Integer, nullable=False),
)

emitters = Table(
    "emitters", metadata,
    Column("id", Text, primary_key=True),
    Column("name", Text, nullable=False),
    Column("flow_lph", Double, nullable=False),
)

plots = Table(
    "plots", metadata,
    Column("id", UuidId, primary_key=True),
    Column("farm_id", UuidId, ForeignKey("farms.id"), nullable=False),
    Column("name", Text, nullable=False),
    Column("area_m2", Double, nullable=False),
    Column("crop_id", Text, ForeignKey("crops.id"), nullable=False),
    Column("planting_date", Date, nullable=False),
    Column("soil_id", Text, ForeignKey("soils.id"), nullable=False),
    Column("row_spacing_m", Double, nullable=False),
    Column("emitter_spacing_m", Double, nullable=False),
    Column("emitter_id", Text, ForeignKey("emitters.id"), nullable=False),
    Column("lat", Double, nullable=False),
    Column("lon", Double, nullable=False),
    UniqueConstraint("farm_id", "name"),
)
