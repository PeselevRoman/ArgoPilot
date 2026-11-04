from fastapi import FastAPI

from catalogues import router as catalogues_router
from errors import add_error_handlers

app = FastAPI(title="AgroPilot registry-service", version="0.1.0")
add_error_handlers(app)
app.include_router(catalogues_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
 