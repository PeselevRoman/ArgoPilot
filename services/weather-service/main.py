"""The HTTP layer: two routes, and the wiring of the forecast service."""

import datetime
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel

import config
from config import Settings
from errors import add_error_handlers
from forecast import Clock, ForecastService, ForecastUnavailable
from provider import SOURCE

# httpx logs every request line at INFO, query string included. With a paid plan the query
# holds the API key, so keep that logger quiet whatever the logging setup is.
logging.getLogger("httpx").setLevel(logging.WARNING)


class DayOut(BaseModel):
    date: datetime.date
    et0_mm: float
    rain_mm: float


class ForecastOut(BaseModel):
    lat: float
    lon: float
    source: str
    fetched_at: str
    stale: bool
    days: list[DayOut]


def _utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def create_app(
    settings: Settings | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
    clock: Clock | None = None,
) -> FastAPI:
    """Build the app. Tests pass fake settings, a fake provider transport and a fake clock."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Reading the settings here makes a missing variable fail at startup, not on the first request.
        app.state.settings = settings or config.get_settings()
        async with httpx.AsyncClient(transport=transport) as client:
            app.state.service = ForecastService(app.state.settings, client, clock or _utc_now)
            yield

    app = FastAPI(title="AgroPilot weather-service", version="0.1.0", lifespan=lifespan)
    add_error_handlers(app)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/forecast", response_model=ForecastOut)
    async def get_forecast(
        request: Request,
        lat: Annotated[float, Query(ge=-90, le=90)],
        lon: Annotated[float, Query(ge=-180, le=180)],
        days: Annotated[int, Query(ge=1, le=7)],
    ) -> ForecastOut:
        try:
            result = await request.app.state.service.get(lat, lon, days)
        except ForecastUnavailable:
            raise HTTPException(
                status_code=503,
                detail="No forecast is available for this point right now",
                headers={"Retry-After": str(request.app.state.settings.retry_after_seconds)},
            ) from None
        return ForecastOut(
            lat=lat,
            lon=lon,
            source=SOURCE,
            fetched_at=result.fetched_at.astimezone(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            stale=result.stale,
            days=[DayOut(date=d.date, et0_mm=d.et0_mm, rain_mm=d.rain_mm) for d in result.days],
        )

    return app


app = create_app()
