"""The planner's clients for the registry and weather services.

Every failure becomes an UpstreamError that names the service and a short
reason, never a URL (httpx error text can carry one). Every body is checked
field by field, like services/weather-service/provider.py: nothing is guessed,
padded or defaulted, because a made-up number would become a watering plan.
"""

import datetime
import math
from dataclasses import dataclass
from urllib.parse import quote

import httpx

from config import Settings
from engine import ForecastDay

REGISTRY = "registry-service"
WEATHER = "weather-service"


class UpstreamError(Exception):
    def __init__(self, service: str, reason: str):
        super().__init__(f"{service} is unavailable: {reason}")
        self.service = service
        self.reason = reason


class PlotNotFound(Exception):
    pass


@dataclass(frozen=True)
class PlotData:
    crop_id: str
    planting_date: datetime.date
    soil_id: str
    area_m2: float
    row_spacing_m: float
    emitter_spacing_m: float
    emitter_id: str
    lat: float
    lon: float


@dataclass(frozen=True)
class Forecast:
    stale: bool
    days: list[ForecastDay]


def _number(service: str, value: object, *, positive: bool = False) -> float:
    # bool is a subclass of int, so it must be refused before the number check.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise UpstreamError(service, "a value is not a number")
    try:
        number = float(value)  # a huge JSON integer overflows here
    except OverflowError:
        raise UpstreamError(service, "a value is too large") from None
    if not math.isfinite(number):
        raise UpstreamError(service, "a value is not finite")
    if number < 0 or (positive and number == 0):
        raise UpstreamError(service, "a value is out of range")
    return 0.0 if number == 0 else number


def _text(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise UpstreamError(REGISTRY, "a text value is missing")
    return value


def _date(service: str, value: object) -> datetime.date:
    if not isinstance(value, str):
        raise UpstreamError(service, "a date is not a string")
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        raise UpstreamError(service, "a date is not an ISO date") from None


def _coordinate(value: object, limit: int) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise UpstreamError(REGISTRY, "a coordinate is not a number")
    try:
        number = float(value)
    except OverflowError:
        raise UpstreamError(REGISTRY, "a coordinate is too large") from None
    if not math.isfinite(number) or abs(number) > limit:
        raise UpstreamError(REGISTRY, "a coordinate is out of range")
    return number


def _segment(identifier: str) -> str:
    """One URL path segment: '/', '?', '#' and '..' in an id cannot change the path."""
    encoded = quote(identifier, safe="")
    return encoded.replace(".", "%2E") if set(encoded) == {"."} else encoded


class Upstream:
    def __init__(self, settings: Settings, client: httpx.AsyncClient):
        self._settings = settings
        self._client = client

    async def _get_json(
        self,
        service: str,
        base: str,
        path: str,
        timeout: float,
        params: dict | None = None,
        not_found: Exception | None = None,
    ) -> object:
        url = f"{base.rstrip('/')}{path}"
        try:
            response = await self._client.get(url, params=params, timeout=httpx.Timeout(timeout))
        except httpx.HTTPError as error:
            # Class name only: str(error) can carry the URL.
            raise UpstreamError(service, type(error).__name__) from None
        if response.status_code == 404 and not_found is not None:
            raise not_found
        if not response.is_success:
            raise UpstreamError(service, f"status {response.status_code}")
        try:
            return response.json()
        except ValueError:
            raise UpstreamError(service, "the body is not JSON") from None

    async def _registry(self, path: str, not_found: Exception | None = None) -> dict:
        body = await self._get_json(
            REGISTRY,
            self._settings.registry_url,
            path,
            self._settings.registry_timeout_seconds,
            not_found=not_found,
        )
        if not isinstance(body, dict):
            raise UpstreamError(REGISTRY, "the body is not an object")
        return body

    async def get_plot(self, plot_id: str) -> PlotData:
        body = await self._registry(f"/v1/plots/{_segment(plot_id)}", not_found=PlotNotFound())
        return PlotData(
            crop_id=_text(body.get("crop_id")),
            planting_date=_date(REGISTRY, body.get("planting_date")),
            soil_id=_text(body.get("soil_id")),
            area_m2=_number(REGISTRY, body.get("area_m2"), positive=True),
            row_spacing_m=_number(REGISTRY, body.get("row_spacing_m"), positive=True),
            emitter_spacing_m=_number(REGISTRY, body.get("emitter_spacing_m"), positive=True),
            emitter_id=_text(body.get("emitter_id")),
            lat=_coordinate(body.get("lat"), 90),
            lon=_coordinate(body.get("lon"), 180),
        )

    async def get_soil_mm_per_m(self, soil_id: str) -> float:
        body = await self._registry(f"/v1/soils/{_segment(soil_id)}")
        return _number(REGISTRY, body.get("available_water_mm_per_m"), positive=True)

    async def get_emitter_flow_lph(self, emitter_id: str) -> float:
        body = await self._registry(f"/v1/emitters/{_segment(emitter_id)}")
        return _number(REGISTRY, body.get("flow_lph"), positive=True)

    async def get_forecast(self, lat: float, lon: float, days: int) -> Forecast:
        body = await self._get_json(
            WEATHER,
            self._settings.weather_url,
            "/v1/forecast",
            self._settings.weather_timeout_seconds,
            params={"lat": lat, "lon": lon, "days": days},
        )
        if not isinstance(body, dict):
            raise UpstreamError(WEATHER, "the body is not an object")
        stale = body.get("stale")
        if not isinstance(stale, bool):
            raise UpstreamError(WEATHER, "stale is missing or not a boolean")
        raw_days = body.get("days")
        if not isinstance(raw_days, list) or len(raw_days) != days:
            raise UpstreamError(WEATHER, f"days is missing or not {days} days long")
        result: list[ForecastDay] = []
        for raw in raw_days:
            if not isinstance(raw, dict):
                raise UpstreamError(WEATHER, "a day is not an object")
            day = _date(WEATHER, raw.get("date"))
            if result and day != result[-1].date + datetime.timedelta(days=1):
                raise UpstreamError(WEATHER, "dates are not consecutive")
            result.append(
                ForecastDay(
                    date=day,
                    et0_mm=_number(WEATHER, raw.get("et0_mm")),
                    rain_mm=_number(WEATHER, raw.get("rain_mm")),
                    stale=stale,
                )
            )
        return Forecast(stale=stale, days=result)
