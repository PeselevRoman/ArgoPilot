"""Test helpers: a fake Open-Meteo, and a clock a test can move."""

from datetime import date, datetime, timedelta

import httpx

import provider


def valid_payload(
    first_day: date,
    days: int = provider.FETCH_DAYS,
    offset: int = 7200,
    et0: float = 3.0,
    rain: float = 0.0,
) -> dict:
    # Open-Meteo's response shape. Only this file and provider.py know it.
    return {
        "utc_offset_seconds": offset,
        "daily_units": {
            "time": "iso8601",
            "et0_fao_evapotranspiration": "mm",
            "precipitation_sum": "mm",
        },
        "daily": {
            "time": [(first_day + timedelta(days=i)).isoformat() for i in range(days)],
            "et0_fao_evapotranspiration": [et0] * days,
            "precipitation_sum": [rain] * days,
        },
    }


class FakeProvider:
    """Answers requests from a script of steps; the last step repeats.

    A step is a payload dict (200), an int (that status, body {}), an
    Exception instance (raised), or "not-json" (200 with a text body).
    """

    def __init__(self, *steps):
        self.steps = list(steps)
        self.calls: list[httpx.Request] = []
        self.transport = httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        index = min(len(self.calls), len(self.steps) - 1)
        self.calls.append(request)
        step = self.steps[index]
        if isinstance(step, Exception):
            raise step
        if step == "not-json":
            return httpx.Response(200, text="<html>not json</html>")
        if isinstance(step, int):
            return httpx.Response(step, json={})
        return httpx.Response(200, json=step)

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=self.transport)


class FakeClock:
    def __init__(self, start: datetime):
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, hours: float = 0, seconds: float = 0) -> None:
        self._now += timedelta(hours=hours, seconds=seconds)
