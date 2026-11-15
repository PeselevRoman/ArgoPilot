"""Start the service against the performance database.

The service code is not changed. This launcher only sets DATABASE_URL
before the server starts, so registry.db is never touched.

The target is a SQLite file path or a database URL.

Usage, from the repository root, with the service's own Python:
    services/registry-service/.venv/bin/python perf/run_server.py perf/perf.db
    services/registry-service/.venv/bin/python perf/run_server.py "$PERF_DATABASE_URL"

The server runs in this one process with one worker. DATABASE_URL is set in
this process's environment, so reload or multiple workers could lose it.
"""

import os
import sys
from pathlib import Path

SERVICE = Path(__file__).resolve().parent.parent / "services" / "registry-service"
sys.path.insert(0, str(SERVICE))

import uvicorn  # noqa: E402
from perf_target import safe, to_url  # noqa: E402

PORT = 8001

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python perf/run_server.py PATH_OR_DATABASE_URL")

    url = to_url(sys.argv[1])
    if url.startswith("sqlite:") and not Path(url.removeprefix("sqlite:///")).exists():
        sys.exit(f"database not found: {url.removeprefix('sqlite:///')}. Create it with perf/seed_perf_db.py first.")

    # to_url gives an absolute SQLite path, so the service does not resolve it against its own folder.
    os.environ["DATABASE_URL"] = url
    print(f"Serving {safe(url)} on port {PORT}")
    uvicorn.run("main:app", host="127.0.0.1", port=PORT, log_level="warning")
