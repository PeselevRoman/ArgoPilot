from datetime import UTC, date, datetime, timedelta

from cache import CacheEntry
from provider import ProviderDay

NOW = datetime(2026, 11, 12, 6, 0, tzinfo=UTC)  # local 08:00 with offset 7200


def entry(first_day: date, count: int = 9, offset: int = 7200, skip: int | None = None) -> CacheEntry:
    days = tuple(
        ProviderDay(first_day + timedelta(days=i), 3.0, 0.0) for i in range(count) if i != skip
    )
    return CacheEntry(fetched_at=NOW, utc_offset_seconds=offset, days=days)


def test_today_is_the_local_date_at_the_point():
    late = datetime(2026, 11, 12, 22, 30, tzinfo=UTC)

    assert entry(date(2026, 11, 12)).today(late) == date(2026, 11, 13)  # +2h crosses midnight
    assert entry(date(2026, 11, 12), offset=0).today(late) == date(2026, 11, 12)


def test_cover_returns_the_first_count_days_from_today():
    days = entry(date(2026, 11, 12)).cover(NOW, 7)

    assert [d.date for d in days] == [date(2026, 11, 12) + timedelta(days=i) for i in range(7)]


def test_cover_drops_days_before_today():
    days = entry(date(2026, 11, 10)).cover(NOW, 7)

    assert days[0].date == date(2026, 11, 12)


def test_cover_is_none_when_too_few_days_remain():
    assert entry(date(2026, 11, 8)).cover(NOW, 7) is None  # only 5 days from today


def test_cover_is_none_when_the_entry_does_not_contain_today():
    assert entry(date(2026, 11, 13)).cover(NOW, 1) is None


def test_cover_is_none_when_a_day_is_missing_in_the_middle():
    assert entry(date(2026, 11, 12), skip=3).cover(NOW, 7) is None


def test_age_is_now_minus_fetched_at():
    assert entry(date(2026, 11, 12)).age(NOW + timedelta(hours=5)) == timedelta(hours=5)
