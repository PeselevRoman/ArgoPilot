import logging
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text

import db

# A tiny app with one route that uses the database dependency.
# It keeps main.py untouched until the real routes exist.
probe_app = FastAPI()


@probe_app.get("/probe")
def probe(conn: sqlite3.Connection = Depends(db.get_db)) -> dict[str, int]:
    return {"foreign_keys": conn.execute("PRAGMA foreign_keys").fetchone()[0]}


client = TestClient(probe_app)


def test_returns_503_with_retry_after_when_database_file_is_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "missing.db")

    response = client.get("/probe")

    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"


def test_returns_503_when_dependency_is_overridden_to_fail():
    def broken_db() -> Iterator[None]:
        raise HTTPException(status_code=503, detail="Database unavailable", headers={"Retry-After": "5"})
        yield  # pragma: no cover

    probe_app.dependency_overrides[db.get_db] = broken_db
    try:
        response = client.get("/probe")
    finally:
        probe_app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"


def test_failed_request_discards_its_writes(monkeypatch, tmp_path):
    # A route that writes and then fails must leave nothing behind.
    database = tmp_path / "registry.db"
    setup = sqlite3.connect(database)
    setup.execute("CREATE TABLE notes (id TEXT PRIMARY KEY)")
    setup.commit()
    setup.close()
    monkeypatch.setattr(db, "DB_PATH", database)

    app = FastAPI()

    @app.post("/write-then-fail")
    def write_then_fail(conn: db.DbConnection) -> None:
        conn.execute("INSERT INTO notes (id) VALUES ('a')")
        raise HTTPException(status_code=409, detail="Nope")

    response = TestClient(app).post("/write-then-fail")

    assert response.status_code == 409
    check = sqlite3.connect(database)
    assert check.execute("SELECT COUNT(*) FROM notes").fetchone()[0] == 0
    check.close()


def test_connects_with_foreign_keys_on_when_database_file_exists(monkeypatch, tmp_path):
    database = tmp_path / "registry.db"
    sqlite3.connect(database).close()
    monkeypatch.setattr(db, "DB_PATH", database)

    response = client.get("/probe")

    assert response.status_code == 200
    assert response.json() == {"foreign_keys": 1}


# --- New SQLAlchemy connection layer (db.Conn), selected by DATABASE_URL ---

new_probe_app = FastAPI()


@new_probe_app.get("/new-probe")
def new_probe(conn: db.Conn) -> dict[str, int]:
    return {"foreign_keys": conn.execute(text("PRAGMA foreign_keys")).scalar_one()}


def test_new_dependency_returns_503_with_retry_after_when_sqlite_file_is_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'missing.db'}")

    response = TestClient(new_probe_app).get("/new-probe")

    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"
    assert not (tmp_path / "missing.db").exists()


def test_new_dependency_returns_503_when_postgres_is_unreachable(monkeypatch, caplog):
    # Port 1 is closed, so a real connection attempt fails.
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/test")

    with caplog.at_level(logging.ERROR, logger="registry.db"):
        response = TestClient(new_probe_app).get("/new-probe")

    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"
    assert any(record.name == "registry.db" for record in caplog.records)


def test_new_dependency_turns_foreign_keys_on(monkeypatch, tmp_path):
    database = tmp_path / "registry.db"
    sqlite3.connect(database).close()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database}")

    response = TestClient(new_probe_app).get("/new-probe")

    assert response.status_code == 200
    assert response.json() == {"foreign_keys": 1}


def _notes_database(tmp_path) -> Path:
    database = tmp_path / "registry.db"
    setup = sqlite3.connect(database)
    setup.execute("CREATE TABLE notes (id TEXT PRIMARY KEY)")
    setup.commit()
    setup.close()
    return database


def test_new_dependency_discards_writes_when_the_route_fails(monkeypatch, tmp_path):
    database = _notes_database(tmp_path)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database}")
    app = FastAPI()

    @app.post("/write-then-fail")
    def write_then_fail(conn: db.Conn) -> None:
        conn.execute(text("INSERT INTO notes (id) VALUES ('a')"))
        raise HTTPException(status_code=409, detail="Nope")

    response = TestClient(app).post("/write-then-fail")

    assert response.status_code == 409
    check = sqlite3.connect(database)
    assert check.execute("SELECT COUNT(*) FROM notes").fetchone()[0] == 0
    check.close()


def test_new_dependency_commits_before_the_response_returns(monkeypatch, tmp_path):
    database = _notes_database(tmp_path)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database}")
    app = FastAPI()

    @app.post("/write")
    def write(conn: db.Conn) -> None:
        conn.execute(text("INSERT INTO notes (id) VALUES ('a')"))

    @app.get("/count")
    def count(conn: db.Conn) -> int:
        return conn.execute(text("SELECT COUNT(*) FROM notes")).scalar_one()

    test_client = TestClient(app)
    assert test_client.post("/write").status_code == 200

    assert test_client.get("/count").json() == 1
