import sqlite3
from collections.abc import Iterator
from pathlib import Path

from fastapi import HTTPException

# Relative on purpose for now: the README starts the server from this folder.
DB_PATH = Path("registry.db")


def get_db() -> Iterator[sqlite3.Connection]:
    # sqlite3.connect() would create a missing file, so check first.
    if not DB_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
            headers={"Retry-After": "5"},
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()
