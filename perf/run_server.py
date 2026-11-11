"""Start the service against the performance database.

The service code is not changed. This launcher only sets DATABASE_URL
before the server starts, so registry.db is never touched.

Usage, from the repository root, with the service's own Python:
    services/registry-service/.venv/bin/python perf/run_server.py perf/perf.db

The server runs in this one process with one worker. DATABASE_URL is set in
this process's environment, so reload or multiple workers could lose it.
"""

import os
import sys
from pathlib import Path

SERVICE = Path(__file__).resolve().parent.parent / "services" / "registry-service"
sys.path.insert(0, str(SERVICE))

import uvicorn  # noqa: E402

PORT = 8001

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python perf/run_server.py PATH_TO_DATABASE")

    database = Path(sys.argv[1]).resolve()
    if not database.exists():
        sys.exit(f"database not found: {database}. Create it with perf/seed_perf_db.py first.")

    # Absolute path, so the service does not resolve it against its own folder.
    os.environ["DATABASE_URL"] = f"sqlite:///{database}"
    uvicorn.run("main:app", host="127.0.0.1", port=PORT, log_level="warning")
