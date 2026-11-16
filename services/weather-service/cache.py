"""Weather cache: the 0.1 degree cell maths (later tasks add storage)."""

from decimal import ROUND_FLOOR, Decimal

# A cell is (latitude tenths, longitude tenths), both rounded down.
Cell = tuple[int, int]


def _tenths(value: float) -> int:
    # For a C# reader: do not write math.floor(value * 10). Floats are binary,
    # so 0.1 + 0.2 != 0.3 (same as double in C#), and 31.3 * 10 can land just
    # below 313.0 and floor to 312. Decimal(str(x)) takes the number as typed
    # and does exact base-10 maths, like C# decimal. ROUND_FLOOR rounds toward
    # minus infinity, so -0.05 goes to cell -1, not 0.
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
