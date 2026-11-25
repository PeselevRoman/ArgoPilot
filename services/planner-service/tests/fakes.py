"""Test helpers: fake registry and weather services behind one httpx.MockTransport."""

import json
from datetime import date, timedelta

import httpx

PLOT_ID = "c8f3d1b0-4d2e-5a1b-8b22-1d6e3f702002"


def plot_json(**overrides) -> dict:
    body = {
        "id": PLOT_ID,
        "farm_id": "farm-1",
        "name": "North block",
        "area_m2": 1000,
        "crop_id": "tomato",
        "planting_date": "2026-03-01",
        "soil_id": "loam",
        "row_spacing_m": 1.5,
        "emitter_spacing_m": 0.4,
        "emitter_id": "dripnet-pc-1.0",
        "lat": 31.25,
        "lon": 34.79,
    }
    body.update(overrides)
    return body


def soil_json(mm=175) -> dict:
    return {"id": "loam", "name": "Loam", "available_water_mm_per_m": mm}


def emitter_json(flow=1.0) -> dict:
    return {"id": "dripnet-pc-1.0", "name": "Drip 1.0", "flow_lph": flow}


def forecast_json(
    start: date, days: int = 7, et0: float = 3.0, rain: float = 0.0, stale: bool = False
) -> dict:
    return {
        "lat": 31.2,
        "lon": 34.7,
        "source": "open-meteo",
        "fetched_at": "2026-11-16T06:00:00Z",
        "stale": stale,
        "days": [
            {"date": (start + timedelta(days=i)).isoformat(), "et0_mm": et0, "rain_mm": rain}
            for i in range(days)
        ],
    }


class FakeUpstreams:
    """Answers registry and weather requests from one step per endpoint.

    A step is a dict (200), an int (that status, body {}), an Exception
    instance (raised), or "not-json" (200 with a text body).
    """

    def __init__(self, plot=None, soil=None, emitter=None, forecast=None):
        self.plot = plot_json() if plot is None else plot
        self.soil = soil_json() if soil is None else soil
        self.emitter = emitter_json() if emitter is None else emitter
        self.forecast = forecast_json(date(2026, 11, 16)) if forecast is None else forecast
        self.calls: list[httpx.Request] = []
        self.transport = httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        host, path = request.url.host, request.url.path
        if host == "registry.test" and path.startswith("/v1/plots/"):
            step = self.plot
        elif host == "registry.test" and path.startswith("/v1/soils/"):
            step = self.soil
        elif host == "registry.test" and path.startswith("/v1/emitters/"):
            step = self.emitter
        elif host == "weather.test" and path == "/v1/forecast":
            step = self.forecast
        else:
            return httpx.Response(404, json={})
        if isinstance(step, Exception):
            raise step
        if step == "not-json":
            return httpx.Response(200, text="<html>not json</html>")
        if isinstance(step, int) and not isinstance(step, bool):
            return httpx.Response(step, json={})
        # json.dumps, not json=: httpx refuses to encode nan, and a test needs to send it.
        return httpx.Response(200, content=json.dumps(step), headers={"content-type": "application/json"})

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=self.transport)
