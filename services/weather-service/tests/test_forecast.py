"""ForecastService with a fake provider and a clock the test moves."""

import logging
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest

from forecast import ForecastService, ForecastUnavailable
from tests.conftest import make_settings
from tests.fakes import FakeClock, FakeProvider, valid_payload

START = datetime(2026, 11, 12, 6, 0, tzinfo=UTC)  # local time 08:00, local today is 2026-11-12
TODAY = date(2026, 11, 12)

pytestmark = pytest.mark.anyio


def build(*steps, **settings):
    fake = FakeProvider(*steps)
    clock = FakeClock(START)
    service = ForecastService(make_settings(**settings), fake.client(), clock.now)
    return service, fake, clock


async def test_first_request_calls_the_provider_once_and_is_not_stale():
    service, fake, _ = build(valid_payload(TODAY))

    result = await service.get(31.25, 34.79, 7)

    assert len(fake.calls) == 1
    assert result.stale is False
    assert result.fetched_at == START
    assert [d.date for d in result.days] == [TODAY + timedelta(days=i) for i in range(7)]


async def test_second_request_in_the_same_cell_makes_no_provider_call():
    service, fake, _ = build(valid_payload(TODAY))

    await service.get(31.21, 34.71, 7)
    result = await service.get(31.29, 34.79, 7)

    assert len(fake.calls) == 1
    assert result.stale is False


async def test_request_in_another_cell_calls_again():
    service, fake, _ = build(valid_payload(TODAY))

    await service.get(31.21, 34.71, 7)
    await service.get(31.31, 34.71, 7)

    assert len(fake.calls) == 2


async def test_entry_older_than_freshness_is_refetched():
    service, fake, clock = build(valid_payload(TODAY))

    await service.get(31.25, 34.79, 7)
    clock.advance(hours=3)
    result = await service.get(31.25, 34.79, 7)

    assert len(fake.calls) == 2
    assert result.stale is False
    assert result.fetched_at == START + timedelta(hours=3)


async def test_fresh_entry_serves_any_days_up_to_seven():
    service, fake, _ = build(valid_payload(TODAY))

    one = await service.get(31.25, 34.79, 1)
    seven = await service.get(31.25, 34.79, 7)

    assert len(fake.calls) == 1
    assert len(one.days) == 1
    assert len(seven.days) == 7


FAILURES = [
    500,
    400,
    "not-json",
    httpx.ConnectTimeout("slow"),
    httpx.ConnectError("down"),
    {"daily": {}},  # a 200 answer that is not a valid forecast
]


@pytest.mark.parametrize("failure", FAILURES, ids=lambda f: type(f).__name__ + str(f)[:12])
async def test_provider_failure_retries_twice_then_serves_stale(failure):
    service, fake, clock = build(valid_payload(TODAY), failure)
    first = await service.get(31.25, 34.79, 7)
    clock.advance(hours=4)

    result = await service.get(31.25, 34.79, 7)

    assert len(fake.calls) == 1 + 3  # one fetch, then 1 attempt + 2 retries
    assert result.stale is True
    assert result.fetched_at == first.fetched_at
    assert result.days == first.days


async def test_retry_succeeds_on_second_attempt():
    service, fake, clock = build(valid_payload(TODAY), 500, valid_payload(TODAY, et0=4.5))
    await service.get(31.25, 34.79, 7)
    clock.advance(hours=4)

    result = await service.get(31.25, 34.79, 7)

    assert len(fake.calls) == 1 + 2
    assert result.stale is False
    assert result.days[0].et0_mm == 4.5


async def test_no_cache_and_provider_down_raises_unavailable():
    service, fake, _ = build(500)

    with pytest.raises(ForecastUnavailable):
        await service.get(31.25, 34.79, 7)

    assert len(fake.calls) == 3


async def test_entry_older_than_max_stale_raises_unavailable():
    service, _, clock = build(valid_payload(TODAY), 500)
    await service.get(31.25, 34.79, 7)
    clock.advance(hours=25)

    with pytest.raises(ForecastUnavailable):
        await service.get(31.25, 34.79, 7)


async def test_stale_entry_that_no_longer_covers_the_days_raises_unavailable():
    # The entry holds days from three days before local today: only 6 days remain from today.
    service, _, clock = build(valid_payload(TODAY - timedelta(days=3)), 500)
    await service.get(31.25, 34.79, 1)  # today is covered, so this works
    clock.advance(hours=4)

    with pytest.raises(ForecastUnavailable):
        await service.get(31.25, 34.79, 7)


async def test_stale_entry_drops_days_already_past():
    service, _, clock = build(valid_payload(date(2026, 11, 12)), 500)
    clock.advance(hours=14)  # 20:00 UTC, local 22:00 on 2026-11-12
    await service.get(31.25, 34.79, 7)
    clock.advance(hours=6)  # local 04:00 on 2026-11-13, entry 6 hours old

    result = await service.get(31.25, 34.79, 7)

    assert result.stale is True
    assert [d.date for d in result.days] == [date(2026, 11, 13) + timedelta(days=i) for i in range(7)]


async def test_invalid_provider_answer_is_not_served_without_a_cache():
    bad = valid_payload(TODAY)
    bad["daily"]["et0_fao_evapotranspiration"][2] = None
    service, _, _ = build(bad)

    with pytest.raises(ForecastUnavailable):
        await service.get(31.25, 34.79, 7)


async def test_invalid_provider_answer_falls_back_to_the_previous_entry():
    bad = valid_payload(TODAY, et0=9.9)
    bad["daily"]["precipitation_sum"][2] = None
    service, _, clock = build(valid_payload(TODAY, et0=3.0), bad)
    await service.get(31.25, 34.79, 7)
    clock.advance(hours=4)

    result = await service.get(31.25, 34.79, 7)

    assert result.stale is True
    assert all(day.et0_mm == 3.0 for day in result.days)


async def test_failure_log_has_no_api_key(caplog):
    service, _, _ = build(500, provider_api_key="SECRET123")

    with caplog.at_level(logging.WARNING), pytest.raises(ForecastUnavailable):
        await service.get(31.25, 34.79, 7)

    assert caplog.records  # something was logged
    assert "SECRET123" not in caplog.text


@pytest.mark.parametrize(
    ("lat", "lon", "expected"),
    [(90, 180, ("90.0", "180.0")), (31.25, 34.79, ("31.25", "34.75"))],
)
async def test_provider_is_asked_for_the_cell_centre_clamped(lat, lon, expected):
    service, fake, _ = build(valid_payload(TODAY))

    await service.get(lat, lon, 7)

    params = fake.calls[0].url.params
    assert (params["latitude"], params["longitude"]) == expected
