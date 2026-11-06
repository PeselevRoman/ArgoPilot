"""Start the service against the performance database.

The service code is not changed. This launcher only sets the database path
before the server starts, so registry.db is never touched.

Usage, from the repository root, with the service's own Python:
    services/registry-service/.venv/bin/python perf/run_server.py perf/perf.db
"""

import sys
from pathlib import Path

SERVICE = Path(__file__).resolve().parent.parent / "services" / "registry-service"
sys.path.insert(0, str(SERVICE))

import db  # noqa: E402
import uvicorn  # noqa: E402

PORT = 8001

if __name__ == "__main__":
    db.DB_PATH = Path(sys.argv[1]).resolve()
    uvicorn.run("main:app", host="127.0.0.1", port=PORT, log_level="warning")
