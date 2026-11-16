"""Weather cache: the 0.1 degree cell maths and the stored forecast entries."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_FLOOR, Decimal

from provider import ProviderDay

# A cell is (latitude tenths, longitude tenths), both rounded down.
Cell = tuple[int, int]


def _tenths(value: float) -> int:
    # For a C# reader: floats are binary, like double in C#, so most decimal
    # fractions are stored a tiny bit off: 0.1 + 0.2 is 0.30000000000000004, and
    # 4.35 * 100 is 434.99999999999994, which math.floor would turn into 434.
    # For one-decimal inputs, math.floor(value * 10) happens to give the right
    # cell (we checked every value from -180.0 to 180.0), but that is luck of the
    # rounding, not something to rely on. Decimal(str(x)) takes the number as
    # typed and does exact base-10 maths, like C# decimal, so the result is
    # right by construction. ROUND_FLOOR rounds toward minus infinity, so
    # -0.05 goes to cell -1, not 0.
    return int((Decimal(str(value)) * 10).to_integral_value(rounding=ROUND_FLOOR))


def cell_of(lat: float, lon: float) -> Cell:
    return (_tenths(lat), _tenths(lon))


def cell_centre(cell: Cell) -> tuple[float, float]:
    """Lower corner of the cell plus 0.05 degrees, clamped to valid ranges."""
    lat_tenths, lon_tenths = cell
    lat = (Decimal(lat_tenths) / 10) + Decimal("0.05")
    lon = (Decimal(lon_tenths) / 10) + Decimal("0.05")
    return (
        float(max(Decimal(-90), min(Decimal(90), lat))),
        float(max(Decimal(-180), min(Decimal(180), lon))),
    )


@dataclass(frozen=True)
class CacheEntry:
    """One cell's forecast as the provider gave it, and when we fetched it."""

    fetched_at: datetime
    utc_offset_seconds: int
    days: tuple[ProviderDay, ...]

    def today(self, now: datetime) -> date:
        # "Today" is the local date at the point, so it works while the provider is down.
        return (now + timedelta(seconds=self.utc_offset_seconds)).date()

    def age(self, now: datetime) -> timedelta:
        return now - self.fetched_at

    def cover(self, now: datetime, count: int) -> list[ProviderDay] | None:
        """The first `count` days from local today, or None if the entry cannot give them.

        None means: too few days left, today is not in the entry, or a day is missing.
        We never pad or guess a missing day.
        """
        today = self.today(now)
        remaining = [day for day in self.days if day.date >= today]
        if len(remaining) < count:
            return None
        chosen = remaining[:count]
        if chosen[0].date != today:
            return None
        for before, after in zip(chosen, chosen[1:]):
            if after.date - before.date != timedelta(days=1):
                return None
        return chosen
