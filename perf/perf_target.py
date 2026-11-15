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
    """Stop before anything is dropped, unless the database is meant to be thrown away.

    SQLite targets are files that the script deletes. A server database is only
    rebuilt when its name contains 'perf', so 'registry' can never be wiped by mistake.
    """
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite":
        return
    name = parsed.database or ""
    if "perf" not in name:
        raise SystemExit(
            f"Refusing to rebuild database '{name}': its name must contain 'perf', "
            "because the script drops and recreates all tables."
        )


def safe(url: str) -> str:
    """The URL with the password hidden, for printing."""
    return make_url(url).render_as_string(hide_password=True)
