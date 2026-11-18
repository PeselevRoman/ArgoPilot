"""The HTTP layer: two routes, and the wiring of the registry and weather clients."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import FastAPI, HTTPException, Query, Request

import config
from config import Settings
from errors import add_error_handlers
from planner import PlanOut, build_plan
from upstream import PlotNotFound, Upstream, UpstreamError


def create_app(
    settings: Settings | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    """Build the app. Tests pass fake settings and a fake transport for both upstream services."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Reading the settings here makes a missing variable fail at startup, not on the first request.
        resolved = settings or config.get_settings()
        async with httpx.AsyncClient(transport=transport) as client:
            app.state.upstream = Upstream(resolved, client)
            yield

    app = FastAPI(title="AgroPilot planner-service", version="0.1.0", lifespan=lifespan)
    add_error_handlers(app)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/plots/{plot_id}/plan", response_model=PlanOut)
    async def get_plan(
        request: Request,
        plot_id: str,
        days: Annotated[int, Query(ge=1, le=7)] = 7,
    ) -> PlanOut:
        try:
            return await build_plan(request.app.state.upstream, plot_id, days)
        except PlotNotFound:
            raise HTTPException(status_code=404, detail="Plot not found") from None
        except UpstreamError as error:
            raise HTTPException(status_code=503, detail=str(error)) from None

    return app


app = create_app()
