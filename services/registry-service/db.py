import logging
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from sqlalchemy import Connection, Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

logger = logging.getLogger("registry.db")

SERVICE_DIR = Path(__file__).parent
ENV_FILE = SERVICE_DIR / ".env"


def load_env_file(path: Path = ENV_FILE) -> None:
    # override=False: a variable already set in the environment wins over the file.
    load_dotenv(path, override=False)


load_env_file()


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is not set. See .env.example.")
    backend = url.split(":", 1)[0].split("+", 1)[0]
    if backend not in ("sqlite", "postgresql", "postgres"):
        raise RuntimeError("DATABASE_URL must start with sqlite: or postgresql:")
    return url


_engines: dict[str, Engine] = {}


def _normalize(url: str) -> str:
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    parsed = make_url(url)
    if parsed.drivername == "sqlite" and parsed.database not in (None, "", ":memory:"):
        # A relative path resolves against the service folder, not the working directory.
        path = Path(parsed.database)
        if not path.is_absolute():
            return parsed.set(database=str(SERVICE_DIR / path)).render_as_string(hide_password=False)
    return url


def get_engine() -> Engine:
    url = _normalize(get_database_url())
    engine = _engines.get(url)
    if engine is None:
        engine = create_engine(url)
        if engine.dialect.name == "sqlite":
            @event.listens_for(engine, "connect")
            def enable_foreign_keys(dbapi_connection, _record) -> None:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys = ON")
                cursor.close()
        _engines[url] = engine
    return engine


def reset_engines() -> None:
    for engine in _engines.values():
        engine.dispose()
    _engines.clear()


def _unavailable() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail="Database unavailable",
        headers={"Retry-After": "5"},
    )


def get_connection() -> Iterator[Connection]:
    engine = get_engine()
    database = engine.url.database
    # SQLite would create a missing file on connect, so check first.
    if engine.dialect.name == "sqlite" and database not in (None, "", ":memory:") and not Path(database).exists():
        logger.error("SQLite database file not found: %s", database)
        raise _unavailable()
    try:
        conn = engine.connect()
    except OperationalError:
        logger.exception("Could not connect to the database")
        raise _unavailable()
    try:
        yield conn
        # One transaction per request: keep the changes only when the route succeeds.
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


Conn = Annotated[Connection, Depends(get_connection, scope="function")]
