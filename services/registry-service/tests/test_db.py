import sqlite3
from collections.abc import Iterator

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

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


def test_connects_with_foreign_keys_on_when_database_file_exists(monkeypatch, tmp_path):
    database = tmp_path / "registry.db"
    sqlite3.connect(database).close()
    monkeypatch.setattr(db, "DB_PATH", database)

    response = client.get("/probe")

    assert response.status_code == 200
    assert response.json() == {"foreign_keys": 1}
