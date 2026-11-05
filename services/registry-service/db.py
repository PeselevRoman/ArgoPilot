import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException

# Resolved from this file's folder, so the server works from any working directory.
DB_PATH = Path(__file__).parent / "registry.db"


def get_db() -> Iterator[sqlite3.Connection]:
    # sqlite3.connect() would create a missing file, so check first.
    if not DB_PATH.exists():
        # 5 seconds is a placeholder. It may change once a real outage shows what fits.
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
        # One transaction per request: keep the changes only when the route succeeds.
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# scope="function" finishes the transaction before the response is sent,
# so a client that reads right after a write always sees it.
DbConnection = Annotated[sqlite3.Connection, Depends(get_db, scope="function")]
