import datetime
import os
import subprocess
import uuid
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

import config
import db

TESTS_DIR = Path(__file__).parent
SEED_SCRIPT = TESTS_DIR / "seed_test_db.sh"
POSTGRES_SCHEMA = TESTS_DIR.parent / "schema.postgres.sql"
CATALOGUES_SEED = TESTS_DIR / "catalogues_seed.sql"

TABLES = ("plots", "farms", "crops", "soils", "emitters")


class TestDatabase:
    # A small helper so tests can read and write rows on either engine.
    __test__ = False  # tell pytest this is not a test class

    def __init__(self, url: str, engine: Engine):
        self.url = url
        self.engine = engine

    def _adapt(self, params: dict) -> dict:
        # SQLite has no uuid or date type: the app stores them as text, so do the same here.
        if self.engine.dialect.name != "sqlite":
            return params
        adapted = {}
        for key, value in params.items():
            if isinstance(value, uuid.UUID):
                value = str(value)
            elif isinstance(value, datetime.date):
                value = value.isoformat()
            adapted[key] = value
        return adapted

    def execute(self, sql: str, **params) -> None:
        with self.engine.begin() as conn:  # begin() commits when the block ends
            conn.execute(text(sql), self._adapt(params))

    def fetch_all(self, sql: str, **params) -> list[tuple]:
        with self.engine.connect() as conn:
            return [tuple(row) for row in conn.execute(text(sql), self._adapt(params))]


def _run_sql_file(engine: Engine, path: Path) -> None:
    statements = [s.strip() for s in path.read_text().split(";") if s.strip()]
    with engine.begin() as conn:
        for statement in statements:
            conn.exec_driver_sql(statement)


@pytest.fixture(params=["sqlite", "postgres"])
def test_db(request, monkeypatch, tmp_path):
    # Runs the test once per engine, like a C# [Theory] with [InlineData].
    if request.param == "sqlite":
        database = tmp_path / "test.db"
        subprocess.run(["bash", str(SEED_SCRIPT), str(database)], check=True)
        url = f"sqlite:///{database}"
        monkeypatch.setenv("DATABASE_URL", url)
        config.get_settings.cache_clear()
        return TestDatabase(url, db.get_engine())

    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set")
    monkeypatch.setenv("DATABASE_URL", url)
    config.get_settings.cache_clear()
    engine = db.get_engine()
    name = engine.url.database or ""
    if "test" not in name:
        pytest.fail(
            f"Refusing to reset database '{name}': its name must contain 'test', "
            "because this fixture drops and recreates all tables."
        )
    with engine.begin() as conn:
        conn.exec_driver_sql(f"DROP TABLE IF EXISTS {', '.join(TABLES)} CASCADE")
    _run_sql_file(engine, POSTGRES_SCHEMA)
    _run_sql_file(engine, CATALOGUES_SEED)
    return TestDatabase(url, engine)


@pytest.fixture(autouse=True)
def clean_database_settings(monkeypatch, tmp_path):
    # A developer's real .env or shell variable must never leak into a test.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(config, "ENV_FILE", tmp_path / "no.env")  # a file that does not exist
    config.get_settings.cache_clear()
    yield
    db.reset_engines()
    config.get_settings.cache_clear()
