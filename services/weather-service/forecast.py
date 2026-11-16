"""The forecast logic: cache, provider, retries, and the stale fallback.

The rule that matters most: a number only reaches a caller if the provider gave
it. If we cannot be sure, we answer "unavailable", never a guess (FR-2.8).
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx

import provider
from cache import CacheEntry, Cell, cell_centre, cell_of
from config import Settings
from provider import ProviderDay, ProviderError

logger = logging.getLogger("weather.forecast")

Clock = Callable[[], datetime]


@dataclass(frozen=True)
class ForecastResult:
    fetched_at: datetime
    stale: bool
    days: list[ProviderDay]


class ForecastUnavailable(Exception):
    """There is no forecast we may serve for this request."""


class ForecastService:
    def __init__(self, settings: Settings, client: httpx.AsyncClient, clock: Clock):
        self._settings = settings
        self._client = client
        self._clock = clock
        self._cache: dict[Cell, CacheEntry] = {}

    async def get(self, lat: float, lon: float, days: int) -> ForecastResult:
        cell = cell_of(lat, lon)
        previous = self._cache.get(cell)
        freshness = timedelta(hours=self._settings.freshness_hours)

        now = self._clock()
        if previous is not None and previous.age(now) < freshness:
            covered = previous.cover(now, days)
            if covered is not None:
                return ForecastResult(previous.fetched_at, False, covered)

        fetched = await self._fetch_with_retries(cell)
        now = self._clock()
        if fetched is not None:
            covered = fetched.cover(now, days)
            if covered is not None:
                return ForecastResult(fetched.fetched_at, False, covered)

        # The provider failed (or gave nothing usable): fall back to the last forecast we kept.
        max_stale = timedelta(hours=self._settings.max_stale_hours)
        if previous is not None and previous.age(now) <= max_stale:
            covered = previous.cover(now, days)
            if covered is not None:
                return ForecastResult(previous.fetched_at, True, covered)
        raise ForecastUnavailable("no usable forecast for this cell")

    async def _fetch_with_retries(self, cell: Cell) -> CacheEntry | None:
        lat, lon = cell_centre(cell)
        attempts = 1 + self._settings.provider_retries
        for attempt in range(1, attempts + 1):
            try:
                result = await provider.fetch(self._client, self._settings, lat, lon)
            except ProviderError as error:
                # The message is safe to log: it never holds the URL or the API key.
                logger.warning("provider attempt %d of %d failed: %s", attempt, attempts, error)
                if attempt < attempts:
                    await asyncio.sleep(self._settings.provider_retry_delay_seconds)
                continue
            entry = CacheEntry(
                fetched_at=self._clock(),
                utc_offset_seconds=result.utc_offset_seconds,
                days=result.days,
            )
            self._cache[cell] = entry
            return entry
        return None
