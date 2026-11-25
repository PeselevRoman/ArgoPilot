# weather-service: design

Decisions are recorded only in `docs/judgment-log-p2.md`. This file describes the design and does not restate the reasoning. Entry already logged: "Stale forecasts are served for up to 24 hours". Pending entries are listed at the end.

Source of requirements: `tasks/p2.md`, section "The `weather-service`" (FR-2.3 to FR-2.8, NFR-2.3) and "Global configurations".

## Intent

The planner needs the next 7 days of ET0 and rain for a point. `weather-service` fetches them from Open-Meteo (the provider), caches them in memory, and serves them over HTTP. It knows coordinates and dates only: nothing about farms, plots or crops. The value of the service is that a provider outage degrades the answer ("stale") instead of breaking it, and that it never returns a number the provider did not give. A forecast of zeros reads as "no water needed", which is the worst bug in the system (FR-2.8).

## Goals

- `GET /v1/forecast?lat&lon&days` as in FR-2.3 to FR-2.7, with the response shape in `tasks/p2.md`.
- `GET /health` returning `{"status": "ok"}` (the frontend status line needs it, FR-2.19). It reports the service's own liveness and does not call the provider.
- Fresh answers fast: p95 at most 100 ms at 10 requests per second, with no provider call (NFR-2.3).
- Provider field names never leave `provider.py`.

## Non-goals and anti-goals

- No database, no persistent cache: a restart empties it.
- No authentication, rate limiting, metrics, Docker, or second provider.
- No back-off memory: after a failed fetch, the next request tries the provider again.
- Anti-goals: a zero, a default, an interpolated or copied day, or any number the provider did not give. A stale forecast older than `MAX_STALE_HOURS`. A password or API key in a log line or response.

## Approaches considered

- **A. Async FastAPI, own dict cache and retry loop (chosen by the learner).** `httpx.AsyncClient`, one in-flight fetch per cell, injectable clock, fake provider through `httpx.MockTransport`.
- **B. Sync FastAPI with threads.** Simpler to read, but shared state across threads needs locks, and a slow provider call holds a worker.
- **C. `cachetools` TTL cache and `tenacity`.** Rejected: a TTL cache evicts at expiry, but the stale fallback needs the expired forecast.

## Behavior

| Situation | Answer |
|---|---|
| `lat` outside -90..90, `lon` outside -180..180, `days` outside 1..7 (integer), a parameter missing, or a non-number such as `nan`/`inf` | `422`, `code: VALIDATION` |
| The cell's forecast is younger than `FRESHNESS_HOURS` (3) | cached forecast, `stale: false`, no provider call |
| Older, provider answers with a valid forecast | store it, answer `stale: false` |
| Provider fails (timeout, error status, not JSON, missing or invalid field) after `PROVIDER_RETRIES` (2) retries, and a cached forecast is at most `MAX_STALE_HOURS` (24) old and still covers the requested days | cached forecast, `stale: true` |
| Provider fails and there is no usable cached forecast | `503`, `code: UNAVAILABLE`, `Retry-After: <RETRY_AFTER_SECONDS>` |

Response: `lat` and `lon` are the requested values, `source` is `"open-meteo"`, `fetched_at` is the UTC time of the provider fetch (ISO 8601 with `Z`), `stale` is for the whole answer, and `days` is a list of `{date, et0_mm, rain_mm}`.

### Cell, days, today

- **Cell:** the point is rounded down to 0.1° on both axes (exact decimal arithmetic, so `31.3` is cell `31.3`, not `31.2`; negative values round toward minus infinity). Two points in one cell share one cache entry. The provider is asked for the cell's centre (cell origin plus 0.05°), clamped into -90..90 and -180..180, so `lat=90` or `lon=180` does not produce an invalid request.
- **Fetch size:** the service always asks the provider for 9 days and caches all of them, whatever `days` was requested, so an entry up to 24 hours old still covers 7 days from today.
- **Today:** the local date at the point. The service requests `timezone=auto`, keeps the provider's `utc_offset_seconds` with the entry, and computes today as `clock.now(UTC) + offset`. Days before today are dropped. The answer takes the next `days` days starting today.
- **Coverage:** the answer is only given if those days exist, are consecutive calendar dates starting today, and are valid. Otherwise the entry is unusable for this request (a fresh entry triggers a refetch, a stale one means `503`).

### What counts as a provider failure

Timeout or connection error; any non-2xx status; a body that is not a JSON object; `daily.time`, `daily.et0_fao_evapotranspiration` or `daily.precipitation_sum` missing or not lists of equal length; a date that is not ISO; a value that is `null`, not a number, a boolean, not finite or negative; `daily_units` for either variable not `"mm"`; fewer than 9 days; dates that are not consecutive. A failure is never repaired: no zero, no default, no neighbour's value.

### Concurrency

Requests for a cell whose entry needs a fetch share one in-flight fetch (an `asyncio.Task` per cell). Every concurrent caller gets that fetch's outcome, including a failure, so a dead provider costs one retry chain, not one per waiting request. When an entry is stored, entries older than `MAX_STALE_HOURS` are purged, so the cache cannot grow forever.

## Configuration (`config.py`, pydantic-settings, `.env`)

All required, no defaults in code, except the API key, which may be empty. The service refuses to start with a clear error if any is missing or invalid.

`PROVIDER_BASE_URL`, `PROVIDER_API_KEY` (sent as the `apikey` query parameter when not empty), `PROVIDER_TIMEOUT_SECONDS`, `PROVIDER_RETRIES`, `PROVIDER_RETRY_DELAY_SECONDS` (pause between attempts; 0 in tests), `FRESHNESS_HOURS`, `MAX_STALE_HOURS`, `RETRY_AFTER_SECONDS`. `.env.example` lists all with safe values (Open-Meteo's public URL, API key empty, retry-after 60). `.env` is never committed or read by the agent.

## Components

`services/weather-service/`, own `.venv`, `pyproject.toml`, `README.md`, `tests/`:

- `config.py`: settings.
- `errors.py`: `application/problem+json` for `VALIDATION`, `UNAVAILABLE`, and the 404/405 mappings. A copy of the registry's behaviour, not an import (services never import each other).
- `provider.py`: the only code that knows Open-Meteo: builds the request, parses and validates the response, returns plain `date`/`float` values and the UTC offset. Holds the source name `"open-meteo"`.
- `cache.py`: cell maths and the stored entries (age, local today, which days an entry can cover).
- `forecast.py`: the logic that ties them together: the cache itself, freshness and the stale limit, the purge, the shared in-flight fetch per cell, retries, cutting days, the stale flag.
- `main.py`: app, routes `/v1/forecast` and `/health`. Port 8001.

## Testing

No real network and no real clock. The provider is a fake behind `httpx.MockTransport`, the clock is injected.

- Unit: cell maths (boundaries `31.3`, `-0.05`, `90`, `180`), cutting days from today, response validation (each failure kind above), the freshness and stale-limit rules.
- API: each validation bound and `nan`; fresh answer with no provider call; same-cell sharing; stale answer after retries (call count is 1 plus `PROVIDER_RETRIES`); `503` with `Retry-After` and no cache; `503` when the cache is older than 24 hours; a stale entry that no longer covers the days; 20 concurrent requests cause one fetch chain, also when it fails; a response of zeros or nulls is never served as numbers.
- Config: missing variable fails at startup.
- Performance (NFR-2.3) stays outside the test suite, next to the registry's check in `perf/`: warm one cell, then 10 requests per second against it, recorded in `perf/results/`.

## Documentation (service README)

The provider's daily variables and units (`et0_fao_evapotranspiration` and `precipitation_sum`, both mm), the stale-limit reasoning, `.env` variables, the example response, and the optional Mermaid sequence diagram (request, fresh or not, provider call, retry, stale answer, `503`).

## Left to the builder

Class and function names inside the files; how to make the clock injectable; the exact message wording; the retry loop's shape; the fake provider used by the performance check; whether `httpx2` and `httpx` can both be installed (the registry's dev dependency is `httpx2`; the service needs `httpx` at runtime).

## Decisions to log (pending the learner's confirmation)

1. The cell is the floor to 0.1°, the provider is asked for the cell centre (clamped), and the response echoes the requested coordinates.
2. Always fetch 9 days; "today" is the local date at the point.
3. Anything outside the strict validity rules is a provider failure, never repaired (null, negative, wrong unit, gaps).
4. Concurrent requests share one fetch and its outcome.
5. Every setting is required in `.env`, except the API key.
