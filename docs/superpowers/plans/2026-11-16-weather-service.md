# weather-service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A new `services/weather-service` that serves the daily ET0 and rain forecast for a point, caches it per 0.1° cell, and degrades to a stale answer or `503` when Open-Meteo fails, never returning a number the provider did not give.

**Architecture:** An async FastAPI app. `provider.py` is the only code that knows Open-Meteo and validates its answer strictly. `cache.py` holds the cell maths and cache entries. `forecast.py` ties them together: freshness, retries, one shared in-flight fetch per cell, stale fallback. `main.py` exposes `/v1/forecast` and `/health`; `errors.py` formats every error as `application/problem+json`.

**Tech Stack:** Python 3.12+, FastAPI, httpx (`AsyncClient`), pydantic-settings, uvicorn, pytest with the anyio pytest plugin for async tests, k6 for the performance check, uv.

**Spec:** `docs/superpowers/specs/2026-11-16-weather-service-design.md`. Requirements come from `tasks/p2.md`, section "The `weather-service`" (FR-2.3 to FR-2.8, NFR-2.3) and "Global configurations". Read `docs/judgment-log-p2.md` first. Record decisions only there, and only after the learner confirms wording: stop, propose the entry, wait.

## Global Constraints

- Work in `services/weather-service` (create it); run tests there with `uv run pytest -q`. `uv run` works only inside a service folder.
- NEVER read any `.env` file (CLAUDE.md rule 11). The code reads it; you do not. Keep `.env.example` complete, with safe values.
- Services never import each other's code. `errors.py` is a copy adapted from `services/registry-service/errors.py`.
- No real network and no real clock in tests: the provider is a fake behind `httpx.MockTransport`, the clock is injected.
- Build only what the design lists: routes `GET /v1/forecast` and `GET /health` only; no database, no persistent cache, no auth, no second provider, no back-off memory.
- FR-2.8: never return a zero, default, interpolated or copied day. A provider answer that is not strictly valid is a failure.
- Open-Meteo field names (`et0_fao_evapotranspiration`, `precipitation_sum`, `daily`, `time`, `utc_offset_seconds`, `daily_units`) appear only in `provider.py` and in tests/fakes that build provider payloads.
- Never log or print the API key or the provider URL's query string. Log the exception class and HTTP status only.
- Constants from the spec: fetch 9 days (`FETCH_DAYS = 9`); `days` request range 1..7; cell = 0.1° (floor); `source` is `"open-meteo"`; defaults for `.env.example`: freshness 3 hours, max stale 24 hours, retries 2, retry-after 60 seconds.
- Error body: `application/problem+json` with `type`, `title`, `status`, `detail`, `code`. Codes used here: `VALIDATION` (422), `UNAVAILABLE` (503, with `Retry-After`), `NOT_FOUND` (404).
- Every commit message ends with the line `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Work is on branch `p2`. Never push.
- Tests for each new file; explain each new file to the learner when it is created (CLAUDE.md rule 10).

## Review Focus

Most likely to bite, each pinned by a test in the owning task:

1. `lat=90`, `lon=180` and `lon=-180`: the cell centre would fall outside the valid range and the provider would answer `400`. The request to the provider must be clamped in range. (Task 2, Task 6)
2. Exact tenths: `lat=31.3` belongs to cell 31.3, not 31.2 (float error), and `-0.05` belongs to the cell below zero. (Task 2)
3. A stale entry that no longer covers the requested days (after local midnight) must give `503`, never a shorter answer. (Task 4)
4. A `200` answer that is not strictly valid: `null`, negative, wrong unit (not `mm`), unequal lengths, fewer than 9 days, gaps in dates. It must never reach a client as numbers. (Task 3)
5. Provider down with many concurrent requests: one retry chain, every waiter gets the same outcome, and a cancelled caller does not cancel the shared fetch. (Task 5)

---

### Task 1: Scaffold and `config.py`

**Files:**
- Create: `services/weather-service/pyproject.toml`, `config.py`, `.env.example`, `tests/conftest.py`, `tests/test_config.py`, `README.md` (stub with run instructions)

**Interfaces:**
- Produces in `config.py`:
  - `ENV_FILE: Path` (absolute path of the service's `.env`, read at call time).
  - `class Settings(BaseSettings)`, `extra="ignore"`, fields: `provider_base_url: str`, `provider_api_key: str = ""`, `provider_timeout_seconds: float`, `provider_retries: int`, `provider_retry_delay_seconds: float`, `freshness_hours: float`, `max_stale_hours: float`, `retry_after_seconds: int`. All except the API key are required. Validation: base URL starts with `http://` or `https://`; timeout > 0; retries >= 0; delay >= 0; freshness > 0; `max_stale_hours >= freshness_hours`; retry-after > 0.
  - `get_settings() -> Settings`, `functools.lru_cache`d, reads `ENV_FILE` at call time, raises `RuntimeError` whose message names the missing or invalid variables (upper-case names, e.g. `PROVIDER_BASE_URL`) and mentions `.env.example`.
- Produces in `tests/conftest.py`: autouse fixture that clears every setting variable from the environment, points `config.ENV_FILE` at a nonexistent temp file and clears `get_settings`'s cache before and after each test; helper `make_settings(**overrides) -> Settings` built with explicit values and `_env_file=None` (defaults: base URL `http://provider.test`, timeout 2, retries 2, delay 0, freshness 3, max stale 24, retry-after 60).

- [ ] **Step 1: Create the project.** `pyproject.toml` named `weather-service`, `requires-python >=3.12`, `package = false` like the registry's. `uv add fastapi httpx pydantic-settings uvicorn` and `uv add --dev pytest httpx2` (the registry uses `httpx2` as the test client dependency). Verify `uv run python -c "import httpx; from fastapi.testclient import TestClient"` succeeds. If `httpx` and `httpx2` conflict, rule on the smallest change that makes both imports work and ledger it. Add `[tool.pytest.ini_options] testpaths=["tests"], pythonpath=["."]`.
- [ ] **Step 2: Write the failing tests in `tests/test_config.py`:** `test_missing_variable_fails_and_names_it` (empty env: `RuntimeError` matching `PROVIDER_BASE_URL`), `test_api_key_may_be_empty`, `test_env_file_is_read` (patch `config.ENV_FILE`), `test_environment_wins_over_env_file`, `test_unrelated_variables_in_env_file_are_ignored`, and a parametrised `test_invalid_value_is_refused` covering each validation rule above (bad URL scheme, timeout 0, retries -1, delay -1, freshness 0, max stale below freshness, retry-after 0).
- [ ] **Step 3: Run `uv run pytest -q`.** Expected: FAIL (no `config` module).
- [ ] **Step 4: Implement `config.py`** following the pattern of `services/registry-service/config.py` (module-level `ENV_FILE`, `Settings(_env_file=ENV_FILE)` inside the cached `get_settings`, `ValidationError` converted to `RuntimeError`).
- [ ] **Step 5: Write `.env.example`** with every variable and a safe value: `PROVIDER_BASE_URL=https://api.open-meteo.com`, `PROVIDER_API_KEY=` (empty), `PROVIDER_TIMEOUT_SECONDS=5`, `PROVIDER_RETRIES=2`, `PROVIDER_RETRY_DELAY_SECONDS=0.5`, `FRESHNESS_HOURS=3`, `MAX_STALE_HOURS=24`, `RETRY_AFTER_SECONDS=60`. README stub: how to create the venv, copy `.env.example` to `.env`, run on port 8001 (`uv run uvicorn main:app --host 127.0.0.1 --port 8001`), run the tests.
- [ ] **Step 6: Run `uv run pytest -q`.** Expected: all pass.
- [ ] **Step 7: Commit** the new folder (not `.venv`, not `.env`): "Scaffold weather-service with pydantic-settings config".

---

### Task 2: Cells

**Files:**
- Create: `cache.py` (cell part only), `tests/test_cells.py`

**Interfaces:**
- Produces in `cache.py`:
  - `Cell = tuple[int, int]` (latitude tenths, longitude tenths, after rounding down).
  - `cell_of(lat: float, lon: float) -> Cell` using exact decimal arithmetic on the text form of the number (`Decimal(str(x))`), rounding toward minus infinity.
  - `cell_centre(cell: Cell) -> tuple[float, float]`: the cell's lower corner plus 0.05°, then clamped into -90..90 and -180..180.

- [ ] **Step 1: Write the failing tests:** `test_cell_of_rounds_down_to_tenths` (31.25, 34.79 → (312, 347)); `test_exact_tenth_belongs_to_its_own_cell` (31.3 → 313, 34.7 → 347, 0.3 → 3, 0.7 → 7, 1.1 → 11); `test_negative_values_round_toward_minus_infinity` (-0.05 → -1, -0.1 → -1, -0.11 → -2); `test_points_in_one_cell_share_it` ((31.2, 34.7) and (31.29, 34.79) equal); `test_adjacent_points_in_different_cells`; `test_centre_is_cell_origin_plus_half_a_tenth` ((312,347) → (31.25, 34.75)); `test_centre_is_clamped_at_the_edges` (`cell_of(90, 180)` centre is (90.0, 180.0); `cell_of(-90, -180)` centre ≥ -90 and ≥ -180).
- [ ] **Step 2: Run them.** Expected: FAIL (`cell_of` missing).
- [ ] **Step 3: Implement** `cell_of` and `cell_centre`. Comment, for a C# reader, why floats are not multiplied by ten (`0.1 + 0.2` problem).
- [ ] **Step 4: Run `uv run pytest -q`.** Expected: all pass.
- [ ] **Step 5: Commit:** "Add the 0.1 degree cell maths".

---

### Task 3: `provider.py` and the test fakes

**Files:**
- Create: `provider.py`, `tests/fakes.py`, `tests/test_provider.py`

**Interfaces:**
- Consumes: `config.Settings`.
- Produces in `provider.py`:
  - `SOURCE = "open-meteo"`, `FETCH_DAYS = 9`.
  - `@dataclass(frozen=True) class ProviderDay: date: datetime.date; et0_mm: float; rain_mm: float`.
  - `@dataclass(frozen=True) class ProviderForecast: utc_offset_seconds: int; days: tuple[ProviderDay, ...]`.
  - `class ProviderError(Exception)`; its message never contains a URL or query string.
  - `parse_response(payload: object) -> ProviderForecast` (pure; raises `ProviderError`). Valid means: a dict; `daily` a dict with `time`, `et0_fao_evapotranspiration`, `precipitation_sum` lists of the same length `FETCH_DAYS`; every date an ISO date and consecutive; every value an `int` or `float` (not `bool`), finite and `>= 0`; `daily_units` for both variables equal to `"mm"`; `utc_offset_seconds` an int.
  - `async fetch(client: httpx.AsyncClient, settings: Settings, lat: float, lon: float) -> ProviderForecast`: one attempt, `GET {base_url}/v1/forecast` with params `latitude`, `longitude`, `daily=et0_fao_evapotranspiration,precipitation_sum`, `forecast_days=9`, `timezone=auto`, plus `apikey` only when the key is not empty; timeout from settings. Any `httpx.HTTPError`, non-2xx status, or non-JSON body becomes `ProviderError`.
- Produces in `tests/fakes.py` (test code, imports `provider` only for constants):
  - `valid_payload(first_day: date, days: int = 9, offset: int = 7200, et0: float = 3.0, rain: float = 0.0) -> dict` in Open-Meteo's response shape.
  - `class FakeProvider(*steps)`: each step is a payload dict (answers 200), an `int` status (answers that status with body `{}`), an `Exception` instance (raised), or the string `"not-json"` (200 with a text body). The last step repeats. Attributes: `calls: list[httpx.Request]`, `transport: httpx.MockTransport`; method `client() -> httpx.AsyncClient`.
  - `class FakeClock(start: datetime)` (timezone-aware UTC) with `now() -> datetime` and `advance(hours: float = 0, seconds: float = 0) -> None`.

- [ ] **Step 1: Write `tests/fakes.py`** as above (helpers for tests; no test of its own).
- [ ] **Step 2: Write the failing tests in `tests/test_provider.py`** (use `@pytest.mark.anyio`, with an `anyio_backend` fixture returning `"asyncio"` in `conftest.py`):
  - `test_parse_returns_nine_days_and_offset` (values equal the payload's).
  - Parametrised `test_parse_refuses_invalid_payload`, one case each: not a dict; `daily` missing; one list missing; a `null` et0; a `null` rain; a string value; a boolean value; a negative et0; negative rain; `nan`; unequal lengths; 8 days; 10 days; a date that is not ISO; a gap between dates; unit `"cm"`; `daily_units` missing; `utc_offset_seconds` missing.
  - `test_fetch_sends_the_documented_request`: captured request has `latitude`, `longitude`, `daily=et0_fao_evapotranspiration,precipitation_sum`, `forecast_days=9`, `timezone=auto`, no `apikey` parameter when the key is empty, and `apikey=<key>` when set.
  - Parametrised `test_fetch_failure_becomes_provider_error`: status 500, status 400, `"not-json"`, `httpx.ConnectTimeout`, `httpx.ConnectError`.
  - `test_provider_error_message_has_no_secret`: with key `SECRET123`, a 500 answer, `"SECRET123" not in str(error)`.
- [ ] **Step 3: Run them.** Expected: FAIL (`provider` missing).
- [ ] **Step 4: Implement `provider.py`.** Validation is explicit and strict; `bool` is checked before `int`/`float` because `True` is an `int` in Python. Explain to the learner why this file is the only one that knows Open-Meteo.
- [ ] **Step 5: Run `uv run pytest -q`.** Expected: all pass.
- [ ] **Step 6: Commit:** "Add the Open-Meteo client with strict validation".

---

### Task 4: Entries, freshness and the forecast logic

**Files:**
- Modify: `cache.py` (add entries)
- Create: `forecast.py`, `tests/test_forecast.py`

**Interfaces:**
- Consumes: `cell_of`, `cell_centre`, `provider.fetch/ProviderForecast/ProviderDay/ProviderError`, `config.Settings`.
- Produces in `cache.py`:
  - `@dataclass(frozen=True) class CacheEntry: fetched_at: datetime; utc_offset_seconds: int; days: tuple[ProviderDay, ...]`.
  - `CacheEntry.today(now: datetime) -> date`: local date at the point, `(now + offset).date()`.
  - `CacheEntry.cover(now: datetime, count: int) -> list[ProviderDay] | None`: the days from local today onward; `None` unless exactly `count` of them exist, the first is today and dates are consecutive.
  - `CacheEntry.age(now: datetime) -> timedelta`.
- Produces in `forecast.py`:
  - `Clock = Callable[[], datetime]`.
  - `@dataclass(frozen=True) class ForecastResult: fetched_at: datetime; stale: bool; days: list[ProviderDay]`.
  - `class ForecastUnavailable(Exception)`.
  - `class ForecastService`: `__init__(self, settings: Settings, client: httpx.AsyncClient, clock: Clock)`; `async def get(self, lat: float, lon: float, days: int) -> ForecastResult`.
- Behavior of `get` (this task: no sharing between concurrent calls yet, that is Task 5): find the cell's entry; if its age is below `freshness_hours` and `cover` is not `None`, return it with `stale=False` and no provider call. Otherwise call the provider for the cell centre with up to `1 + provider_retries` attempts, sleeping `provider_retry_delay_seconds` between attempts (`asyncio.sleep`); the first valid answer is stored (`fetched_at` = `clock()`) and returned if it covers the request, `stale=False`. If all attempts fail, or the new entry does not cover the request, fall back to the previous entry only if its age is `<= max_stale_hours` and `cover` is not `None`: return it with `stale=True`. Otherwise raise `ForecastUnavailable`. Log each failed attempt at WARNING level with the exception class and the HTTP status only.

- [ ] **Step 1: Write the failing tests in `tests/test_forecast.py`** (anyio, `FakeProvider`, `FakeClock`, `make_settings`; clock starts `2026-11-12 06:00 UTC`, offset 7200, so local today is `2026-11-12`):
  - `test_first_request_calls_the_provider_once_and_is_not_stale`
  - `test_second_request_in_the_same_cell_makes_no_provider_call` (31.21, 34.71 then 31.29, 34.79: one call)
  - `test_request_in_another_cell_calls_again`
  - `test_entry_older_than_freshness_is_refetched` (advance 3 hours: second call)
  - `test_fresh_entry_serves_any_days_up_to_seven` (fetch with days=1, then days=7: one call)
  - `test_provider_failure_retries_twice_then_serves_stale` (first call OK; advance 4 hours; provider then fails with each failure kind; assert exactly 3 provider calls in that round, `stale=True`, and the same `fetched_at` as before)
  - `test_retry_succeeds_on_second_attempt` (failure then payload: 2 calls, `stale=False`)
  - `test_no_cache_and_provider_down_raises_unavailable` (3 calls)
  - `test_entry_older_than_max_stale_raises_unavailable` (advance 25 hours, provider down)
  - `test_stale_entry_that_no_longer_covers_the_days_raises_unavailable`: the fake provider answers with `valid_payload(first_day=local_today - 3 days)`, so the stored entry holds only 6 days from local today. A first request with `days=1` succeeds (today is covered). Advance 4 hours, make the provider fail, request `days=7`: `ForecastUnavailable`, not a shorter list.
  - `test_stale_entry_drops_days_already_past`: clock starts `2026-11-12 20:00 UTC` (22:00 local), payload `first_day=2026-11-12`, first request succeeds; advance 6 hours (local `2026-11-13 04:00`, entry 6 hours old), provider fails, request `days=7`: `stale=True`, seven consecutive dates starting `2026-11-13`.
  - `test_invalid_provider_answer_is_not_served` (a 200 with a `null` day: with no cache raises `ForecastUnavailable`; with a stale cache serves the previous entry, never the bad answer).
  - `test_failure_log_has_no_api_key` (key `SECRET123`, provider fails; `caplog.text` lacks it).
  - `test_provider_is_asked_for_the_cell_centre_clamped` (request `lat=90, lon=180`: captured `latitude` and `longitude` are `90.0` and `180.0`; request `31.25, 34.79`: `31.25` and `34.75`).
- [ ] **Step 2: Run them.** Expected: FAIL (`forecast` missing).
- [ ] **Step 3: Implement `CacheEntry` in `cache.py` and `ForecastService.get` in `forecast.py`** as specified. Keep the cache as a plain `dict[Cell, CacheEntry]` owned by the service.
- [ ] **Step 4: Run `uv run pytest -q`.** Expected: all pass.
- [ ] **Step 5: Commit:** "Add the forecast logic with retries and the stale fallback".

---

### Task 5: One shared fetch per cell, and the purge

**Files:**
- Modify: `forecast.py`, `cache.py` (purge helper if useful), `tests/test_forecast.py`

**Interfaces:**
- Consumes: Task 4's `ForecastService`.
- Produces: `ForecastService.get` unchanged in signature. Concurrent calls whose cell needs a provider round share one `asyncio.Task` per cell (the whole retry chain). Every caller of that chain receives its outcome, including a failure. Callers await it through `asyncio.shield`, so cancelling one caller does not cancel the shared task. After a chain finishes, the task is removed from the in-flight map. Storing an entry removes entries older than `max_stale_hours`.

- [ ] **Step 1: Write the failing tests** (anyio):
  - `test_twenty_concurrent_requests_for_one_cell_make_one_provider_call` (`asyncio.gather`, a provider that yields control once before answering so calls truly overlap; 1 call, 20 equal results).
  - `test_concurrent_requests_share_a_failure` (provider always fails, no cache: 3 provider calls in total, all 20 callers raise `ForecastUnavailable`).
  - `test_concurrent_requests_share_a_stale_answer` (stale entry, provider down: 3 calls, 20 results with `stale=True`).
  - `test_different_cells_fetch_in_parallel` (two cells: 2 calls).
  - `test_cancelling_one_caller_does_not_fail_the_others` (cancel one of three waiting tasks; the other two still get results; one provider call).
  - `test_inflight_entry_is_removed_after_the_round` (a later request after a failed round tries the provider again).
  - `test_old_entries_are_purged_when_a_new_one_is_stored` (store cell A, advance 25 hours, fetch cell B, then the service's cache no longer holds A; expose a read-only `cache_size` property for this).
- [ ] **Step 2: Run them.** Expected: FAIL (the Task 4 code makes one call per request).
- [ ] **Step 3: Implement** the shared task and the purge. Explain to the learner what `asyncio.Task` and `asyncio.shield` are, with the C# `Task` / `CancellationToken` comparison.
- [ ] **Step 4: Run `uv run pytest -q`.** Expected: all pass.
- [ ] **Step 5: Commit:** "Share one provider fetch per cell and purge old entries".

---

### Task 6: HTTP layer: routes and errors

**Files:**
- Create: `errors.py`, `main.py`, `tests/test_api.py`

**Interfaces:**
- Consumes: `ForecastService`, `ForecastUnavailable`, `provider.SOURCE`, `config.get_settings`.
- Produces:
  - `errors.add_error_handlers(app: FastAPI) -> None`: copy of the registry's `errors.py` with `409` removed. `503` maps to `UNAVAILABLE`; `404` to `NOT_FOUND`; `405` and `400` and `422` to `VALIDATION`. Validation messages name the field.
  - `main.create_app(settings: Settings | None = None, transport: httpx.AsyncBaseTransport | None = None, clock: Clock | None = None) -> FastAPI`. The lifespan builds the settings (`get_settings()` when none given, so a missing variable fails at startup), one `httpx.AsyncClient(transport=transport)` closed on shutdown, and the `ForecastService` (default clock: `datetime.now(timezone.utc)`).
  - `main.app = create_app()` for `uvicorn main:app`.
  - `GET /health` → `{"status": "ok"}`.
  - `GET /v1/forecast` with required query parameters `lat: float` in [-90, 90], `lon: float` in [-180, 180], `days: int` in [1, 7].
  - Response body: `{"lat", "lon", "source", "fetched_at", "stale", "days": [{"date", "et0_mm", "rain_mm"}]}`; `lat`/`lon` echo the request, `source` is `"open-meteo"`, `fetched_at` is UTC with a `Z` suffix and no fractional seconds (`2026-11-12T06:00:00Z`), `date` is `YYYY-MM-DD`.
  - `ForecastUnavailable` → `503`, `code: UNAVAILABLE`, header `Retry-After: <retry_after_seconds>`.

- [ ] **Step 1: Write the failing tests in `tests/test_api.py`** (`TestClient(create_app(make_settings(), transport=fake.transport, clock=clock.now))` used as a context manager):
  - `test_forecast_returns_the_documented_shape` (exact JSON for a known payload: `lat 31.25`, `lon 34.79`, `days=7`, 7 days, `source`, `fetched_at` `"2026-11-12T06:00:00Z"`, `stale false`).
  - `test_days_is_cut_to_the_request` (`days=3` → 3 items).
  - `test_fresh_request_does_not_call_the_provider_again`.
  - `test_stale_answer_has_stale_true` and `test_stale_answer_keeps_the_original_fetched_at`.
  - `test_503_when_provider_down_and_no_cache` (status, `application/problem+json`, `code` `UNAVAILABLE`, `Retry-After: 60`).
  - Parametrised `test_validation_errors_are_422_validation`: lat 90.1, -90.1, lon 180.1, -180.1, days 0, days 8, days 3.5, days `abc`, lat `abc`, lat `nan`, lat `inf`, lon `nan`, missing lat, missing lon, missing days. Each: 422, `application/problem+json`, `code` `VALIDATION`, and no provider call.
  - `test_boundaries_are_accepted` (lat ±90, lon ±180, days 1 and 7 give 200; the provider's captured request has `latitude` within [-90, 90] and `longitude` within [-180, 180]).
  - `test_unknown_route_is_404_not_found`, `test_wrong_method_is_405_problem_json`.
  - `test_health_ok` and `test_health_does_not_call_the_provider`.
  - `test_response_never_contains_provider_field_names` (response text has no `et0_fao_evapotranspiration` or `precipitation_sum`).
  - `test_app_refuses_to_start_without_settings` (entering `TestClient(create_app())` with an empty environment raises `RuntimeError` naming `PROVIDER_BASE_URL`).
- [ ] **Step 2: Run them.** Expected: FAIL (`main` missing).
- [ ] **Step 3: Implement `errors.py` and `main.py`.** Response models are pydantic classes so the JSON shape is fixed in one place; serialise `fetched_at` with `strftime("%Y-%m-%dT%H:%M:%SZ")` on the UTC datetime.
- [ ] **Step 4: Run `uv run pytest -q`.** Expected: all pass.
- [ ] **Step 5: Commit:** "Add the forecast route, health route and problem+json errors".

---

### Task 7: README and a real-provider smoke check

**Files:**
- Modify: `services/weather-service/README.md`

- [ ] **Step 1: Write the README:** what the service does and does not know; the endpoint with parameters and error table (422, 503, plus `Retry-After`); the example response from the spec; the provider's daily variables and units (`et0_fao_evapotranspiration`, `precipitation_sum`, both mm, verified against the live API on 2026-11-15) and the fields kept inside `provider.py`; every `.env` variable and what it does; the stale-limit decision (24 hours) and why, in the learner's words from `docs/judgment-log-p2.md`; the cell, 9-day fetch and "today" rules; a file table (`config.py`, `errors.py`, `provider.py`, `cache.py`, `forecast.py`, `main.py`, `tests/`); how to run the tests. Optional: a Mermaid sequence diagram (request, fresh or not, provider call, retry, stale answer, 503).
- [ ] **Step 2: Real smoke check.** Ask the learner to run `cp .env.example .env` in `services/weather-service` (do not read the file). Start `uv run uvicorn main:app --host 127.0.0.1 --port 8001` in the background and run `curl -s "http://127.0.0.1:8001/v1/forecast?lat=31.25&lon=34.79&days=7"`. Expected: 200, 7 days starting today's local date, `stale: false`. Repeat the call: the same `fetched_at` (served from cache). Stop the server. Report the numbers faithfully; if the provider is unreachable, say so and do not retry until green.
- [ ] **Step 3: Check the README example against the real response shape** and fix any difference in the README, not in the code.
- [ ] **Step 4: Commit:** "Document weather-service".

---

### Task 8: Performance check for NFR-2.3

**Files:**
- Create: `perf/weather_nfr_2_3.js`, `perf/run_weather_server.py`, `perf/record_weather_results.py`, `perf/tests/test_weather_perf.py`

**Interfaces:**
- Consumes: `weather-service` `main.create_app`, `tests`-independent: the launcher builds its own fake provider payload.
- Produces in `perf/run_weather_server.py`: `fake_payload(first_day: datetime.date) -> dict` (a valid 9-day Open-Meteo-shaped payload, offset 7200); a launcher that sets the required settings variables for the run, builds the app with `create_app(transport=httpx.MockTransport(...))` answering that payload, and serves it on port 8011 (the registry's perf server uses 8001). No internet is needed.

- [ ] **Step 1: Write the failing test** `test_fake_payload_is_accepted_by_the_real_validator`: `provider.parse_response(fake_payload(date(2026, 11, 12)))` returns 9 days. The test file adds `services/weather-service` to `sys.path`. Run it with the registry venv's pattern, from the repo root, using the weather service's own Python: `services/weather-service/.venv/bin/python -m pytest perf/tests/test_weather_perf.py -q`. Expected: FAIL.
- [ ] **Step 2: Implement the launcher** (`run_weather_server.py`), modelled on `perf/run_server.py`, plus `weather_nfr_2_3.js`: a `setup()` that sends one request to warm the cell, then 10 requests per second for 60 seconds at `GET /v1/forecast?lat=31.25&lon=34.79&days=7`, with a `http_req_duration` p95 threshold below 100 ms and a check that every answer is 200 with `stale` false.
- [ ] **Step 3: Implement `record_weather_results.py`:** reads a k6 summary, writes `perf/results/<UTC time>_weather_v<version>.md` with version, commit, k6 version, p95, failed-request rate, and Pass/Fail against the 100 ms target.
- [ ] **Step 4: Run the test and the weather suite.** Expected: pass. Then run the check: start the launcher in the background, `k6 run --summary-export <scratchpad>/summary.json perf/weather_nfr_2_3.js`, `python3 perf/record_weather_results.py <scratchpad>/summary.json`, stop the server.
- [ ] **Step 5: Report faithfully.** State the measured p95 against 100 ms. If it is over, report and stop; do not tune until green.
- [ ] **Step 6: Add the measured number and the commands to the weather README, and commit** the perf files and the result: "Add and record the weather performance check".

---

## Self-Review

- **Spec coverage:** FR-2.3 shape and `days` (Tasks 4, 6); FR-2.4 validation (Task 6); FR-2.5 cell and freshness (Tasks 2, 4); FR-2.6 retries and stale (Task 4); FR-2.7 `503` and `Retry-After` (Tasks 4, 6); FR-2.8 strict validation (Task 3, also the cover rule in Task 4); NFR-2.3 (Task 8); config and `.env.example` (Task 1); provider fields, units and stale-limit documented (Task 7); optional diagram (Task 7); `/health` (Task 6); single-flight, purge, clamp, today-from-offset, nine-day fetch (Tasks 2 to 5).
- **Names:** `cell_of`, `cell_centre`, `CacheEntry.cover/today/age`, `ForecastService.get`, `ForecastResult`, `ForecastUnavailable`, `create_app`, `make_settings`, `FakeProvider`, `FakeClock`, `valid_payload` and `fake_payload` are used the same way wherever they appear.
- **Decisions awaiting the learner's confirmation** (propose wording, wait, then write to `docs/judgment-log-p2.md`): the five listed at the end of the design.
