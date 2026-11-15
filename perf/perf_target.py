"""Helpers shared by the performance scripts: which database to use, and when it is safe to rebuild.

Run with the service's own Python (it needs SQLAlchemy).
"""

from pathlib import Path

from sqlalchemy.engine import make_url


def to_url(target: str) -> str:
    """A database URL is kept as it is; anything else is a SQLite file path."""
    if not target.strip():
        # An empty shell variable (for example an unset PERF_DATABASE_URL) must not turn into the current folder.
        raise SystemExit("No database given. Is PERF_DATABASE_URL set in this terminal?")
    if "://" in target:
        return target
    return f"sqlite:///{Path(target).resolve()}"


def check_rebuildable(url: str) -> None:
    """Stop before anything is deleted or dropped, unless the target is meant to be thrown away.

    The database name (for a SQLite file: the file name) must contain 'perf', so
    'registry' or 'registry.db' can never be wiped by a typo.
    """
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite":
        name = Path(parsed.database or "").name
    else:
        # The driver lets a query parameter override the database in the path, which would
        # make this check look at the wrong name.
        if {"dbname", "database"} & set(parsed.query):
            raise SystemExit("Refusing a URL with a dbname or database query parameter. Put the name in the path.")
        name = parsed.database or ""
    if "perf" not in name:
        raise SystemExit(
            f"Refusing to rebuild '{name}': its name must contain 'perf', "
            "because the script deletes or drops everything in it."
        )


def safe(url: str) -> str:
    """The URL with the password hidden, for printing."""
    return make_url(url).render_as_string(hide_password=True)
