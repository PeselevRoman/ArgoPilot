from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

import db
from catalogues import router as catalogues_router
from errors import add_error_handlers
from farms import router as farms_router
from plots import router as plots_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Fail at startup, not on the first request, when DATABASE_URL is missing or wrong.
    db.get_database_url()
    yield


app = FastAPI(title="AgroPilot registry-service", version="0.1.0", lifespan=lifespan)
add_error_handlers(app)
app.include_router(catalogues_router)
app.include_router(farms_router)
app.include_router(plots_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
 