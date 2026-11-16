"""The Open-Meteo client. This is the only file that knows Open-Meteo's field names.

Everything else in the service sees ProviderForecast, so swapping the provider
means rewriting this file alone (like an adapter behind an interface in C#).
"""

import datetime
import math
from dataclasses import dataclass

import httpx

from config import Settings

SOURCE = "open-meteo"
FETCH_DAYS = 9

_ET0 = "et0_fao_evapotranspiration"
_RAIN = "precipitation_sum"


@dataclass(frozen=True)
class ProviderDay:
    date: datetime.date
    et0_mm: float
    rain_mm: float


@dataclass(frozen=True)
class ProviderForecast:
    utc_offset_seconds: int
    days: tuple[ProviderDay, ...]


class ProviderError(Exception):
    """The provider failed or answered with something unusable.

    The message never holds a URL, a query string or the API key.
    """


def _number(value: object) -> float:
    # bool is a subclass of int, so it must be refused before the number check.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProviderError("provider value is not a number")
    if not math.isfinite(value) or value < 0:
        raise ProviderError("provider value is not a finite non-negative number")
    return float(value)


def parse_response(payload: object) -> ProviderForecast:
    if not isinstance(payload, dict):
        raise ProviderError("provider payload is not an object")
    offset = payload.get("utc_offset_seconds")
    if isinstance(offset, bool) or not isinstance(offset, int):
        raise ProviderError("provider utc offset is missing or not an integer")
    units = payload.get("daily_units")
    if not isinstance(units, dict) or units.get(_ET0) != "mm" or units.get(_RAIN) != "mm":
        raise ProviderError("provider units are missing or not mm")
    daily = payload.get("daily")
    if not isinstance(daily, dict):
        raise ProviderError("provider daily block is missing")
    times, et0s, rains = daily.get("time"), daily.get(_ET0), daily.get(_RAIN)
    for series in (times, et0s, rains):
        if not isinstance(series, list) or len(series) != FETCH_DAYS:
            raise ProviderError(f"provider series is missing or not {FETCH_DAYS} days long")

    days = []
    for raw_date, raw_et0, raw_rain in zip(times, et0s, rains):
        if not isinstance(raw_date, str):
            raise ProviderError("provider date is not a string")
        try:
            day = datetime.date.fromisoformat(raw_date)
        except ValueError:
            raise ProviderError("provider date is not an ISO date") from None
        if days and day != days[-1].date + datetime.timedelta(days=1):
            raise ProviderError("provider dates are not consecutive")
        days.append(ProviderDay(day, _number(raw_et0), _number(raw_rain)))
    return ProviderForecast(offset, tuple(days))


async def fetch(client: httpx.AsyncClient, settings: Settings, lat: float, lon: float) -> ProviderForecast:
    """One attempt. Any failure becomes a ProviderError naming only the kind of failure."""
    params: dict[str, str | float | int] = {
        "latitude": lat,
        "longitude": lon,
        "daily": f"{_ET0},{_RAIN}",
        "forecast_days": FETCH_DAYS,
        "timezone": "auto",
    }
    if settings.provider_api_key:
        params["apikey"] = settings.provider_api_key
    url = f"{settings.provider_base_url.rstrip('/')}/v1/forecast"
    try:
        response = await client.get(url, params=params, timeout=settings.provider_timeout_seconds)
    except httpx.HTTPError as error:
        # Class name only: str(error) can carry the URL and the API key.
        raise ProviderError(f"provider request failed: {type(error).__name__}") from None
    if not response.is_success:
        raise ProviderError(f"provider answered status {response.status_code}")
    try:
        payload = response.json()
    except ValueError:
        raise ProviderError("provider answered with a body that is not JSON") from None
    return parse_response(payload)
