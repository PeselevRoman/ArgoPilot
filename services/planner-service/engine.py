"""Temporary: only ForecastDay, which upstream.py needs. The engine itself comes in a later task."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ForecastDay:
    date: date
    et0_mm: float
    rain_mm: float
    stale: bool
