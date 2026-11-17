# planner-service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A new `services/planner-service` that turns a registry plot and a weather forecast into a 1 to 7 day irrigation plan, with every irrigation number calculated by one pure engine that follows the `irrigation-calc-reference` skill.

**Architecture:** `engine.py` is pure (no network, no clock): single crop coefficient, soil bucket, litres, run minutes. `upstream.py` calls the registry and the weather service with strict validation and names the failing service. `planner.py` ties them together and rounds the response; `main.py` exposes `/v1/plots/{id}/plan` and `/health`. Crop numbers live in a cited Python module, `crops.py`.

**Tech Stack:** Python 3.12+, FastAPI, httpx (`AsyncClient`), pydantic-settings, uvicorn, pytest with the anyio plugin, uv.

**Spec:** `docs/superpowers/specs/2026-11-16-planner-service-design.md`. Requirements: `tasks/p2.md`, "The `planner-service`" (FR-2.9 to FR-2.14) and "Global configurations". Domain source: `services/planner-service/docs/research/fao56.md`. Read `docs/judgment-log-p2.md` first. Record decisions only there, and only after the learner confirms wording: stop, propose the entry, wait.

## Global Constraints

- Work in `services/planner-service`; run tests there with `uv run pytest -q`. `uv run` works only inside a service folder.
- NEVER read any `.env` file (CLAUDE.md rule 11). Keep `.env.example` complete, with safe values.
- Services never import each other's code. `errors.py` and test helpers are copies adapted from `services/weather-service`.
- No real network and no real clock in tests: upstream services are fakes behind `httpx.MockTransport`.
- Build only what the design lists: routes `GET /v1/plots/{id}/plan` and `GET /health` only; no database, no stored plans, no retries or caching of upstream answers, no dual coefficient (FAO-56 Chapter 7 is out of scope), no performance check.
- Rule 12: every irrigation number is calculated in `engine.py` and nowhere else. No AI model computes or adjusts a number.
- Rule 6: the response has only the fields in the spec: top level `plot_id`, `days`; per day `date`, `et0_mm`, `kc`, `litres`, `run_minutes`, `stale`, `bucket_mm` (FR-2.10 no longer lists `need_mm`; the engine's irrigation depth `irrigation_mm` is internal and never returned).
- Never a plan of zeros: any upstream failure or invalid upstream answer gives `503` with `code: UPSTREAM_UNAVAILABLE` and a `detail` naming the service (`registry-service` or `weather-service`). The planner never pads a missing forecast day.
- Error body: `application/problem+json` with `type`, `title`, `status`, `detail`, `code`. Codes here: `VALIDATION` (422, also 405), `NOT_FOUND` (404), `UPSTREAM_UNAVAILABLE` (503).
- Never log or print upstream URLs with credentials; log the service name, exception class and HTTP status only.
- Crop table (`crops.py`, provisional, cited): `tomato`: Kc 0.6 / 1.15 / 0.80, stages 30/40/45/30 days, `Zr` 0.7 m, `p` 0.40. `bell-pepper`: Kc 0.6 / 1.05 / 0.90, stages 30/35/40/20, `Zr` 0.5 m, `p` 0.30.
- Rounding only in the response: 2 decimals for `et0_mm`, `litres`, `run_minutes`, `bucket_mm`; 3 for `kc`. Accuracy: within 0.5% of the hand-calculated cases (our own standard).
- Every commit message ends with the line `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Work is on branch `p2`. Never push.
- Tests for each new file; explain each new file to the learner when it is created (CLAUDE.md rule 10).

## Review Focus

Most likely to bite, each pinned by a test in the owning task:

1. A `200` upstream answer that contains no usable data (an empty `days`, `null` values, a forecast with fewer days than asked) must give `503` naming the weather service, never a plan of zeros. (Task 5, Task 6)
2. Kc off-by-one at stage boundaries: the planting day, the last day of each stage, and the first day of the next. (Task 4)
3. A plot past its season, and a `planting_date` after the forecast's first date: Kc end, and day 1 (never a negative day index). (Task 4)
4. Rain larger than the depletion, and an irrigation never larger than the depletion; the depletion never above `TAW`. (Task 4)
5. Both upstream services failing: the registry's failure is reported (deterministic), and a malformed plot id gives `404`. (Task 6)

---

### Task 1: Scaffold and `config.py`

**Files:**
- Create: `services/planner-service/pyproject.toml`, `config.py`, `.env.example`, `tests/conftest.py`, `tests/test_config.py`, `README.md` (stub)

**Interfaces:**
- Produces in `config.py`: `ENV_FILE: Path` (absolute, read at call time); `class Settings(BaseSettings)` with `extra="ignore"`, `allow_inf_nan=False` and required fields `registry_url: str`, `weather_url: str`, `registry_timeout_seconds: float`, `weather_timeout_seconds: float` (no defaults); `get_settings() -> Settings` (`lru_cache`d, builds `Settings(_env_file=ENV_FILE)`, converts a validation failure to `RuntimeError` whose message names the upper-case variables and mentions `.env.example`). Validation: URLs start with `http://` or `https://` (stripped); timeouts above 0 and at most 600.
- Produces in `tests/conftest.py`: autouse fixture clearing `REGISTRY_URL`, `WEATHER_URL`, `REGISTRY_TIMEOUT_SECONDS`, `WEATHER_TIMEOUT_SECONDS` from the environment, pointing `config.ENV_FILE` at a nonexistent temp file and clearing `get_settings`'s cache before and after each test; `anyio_backend` fixture returning `"asyncio"`; `make_settings(**overrides) -> Settings` (explicit values, `_env_file=None`; defaults: registry `http://registry.test`, weather `http://weather.test`, timeouts 2 and 5).

- [ ] **Step 1: Create the project** following `services/weather-service/pyproject.toml` (name `planner-service`, `package = false`, same pytest settings). `uv add fastapi httpx pydantic-settings uvicorn` and `uv add --dev pytest httpx2`. Verify `uv run python -c "import httpx; from fastapi.testclient import TestClient"`.
- [ ] **Step 2: Write the failing tests in `tests/test_config.py`:** `test_missing_variable_fails_and_names_it`, `test_error_mentions_env_example`, `test_env_file_is_read`, `test_environment_wins_over_env_file`, `test_unrelated_variables_in_env_file_are_ignored`, parametrised `test_invalid_value_is_refused` (bad URL scheme for each URL; timeout 0; timeout 601), parametrised `test_non_finite_timeout_is_refused` (`nan`, `inf`, `-inf`).
- [ ] **Step 3: Run `uv run pytest -q`.** Expected: FAIL (no `config` module).
- [ ] **Step 4: Implement `config.py`** following `services/weather-service/config.py`.
- [ ] **Step 5: Write `.env.example`** (`REGISTRY_URL=http://127.0.0.1:8000`, `WEATHER_URL=http://127.0.0.1:8001`, `REGISTRY_TIMEOUT_SECONDS=5`, `WEATHER_TIMEOUT_SECONDS=30`) and a README stub (setup, run on port 8002 with `uv run uvicorn main:app --host 127.0.0.1 --port 8002`, tests).
- [ ] **Step 6: Run `uv run pytest -q`.** Expected: all pass.
- [ ] **Step 7: Commit** the folder (not `.venv`, not `.env`; `docs/research/fao56.md` is already committed): "Scaffold planner-service with pydantic-settings config".

---

### Task 2: The `irrigation-calc-reference` skill and the three hand-calculated cases

**Files:**
- Create: `.claude/skills/irrigation-calc-reference/SKILL.md`, `services/planner-service/tests/cases.py`

This task needs the learner. The implementer writes the skill, then stops for the hand calculations.

**Interfaces:**
- Produces: the skill file (formulas, units, three cases, a pointer to `services/planner-service/docs/research/fao56.md`); `tests/cases.py` holding the three cases as data (see Step 3), read by Task 4's tests.

- [ ] **Step 1: Write `SKILL.md`.** Frontmatter `name: irrigation-calc-reference` and a `description` that says when to use it (any code or review touching the planner's irrigation numbers). Sections: **How to use** (formulas are authoritative for `engine.py`; sources in `fao56.md`; values in `crops.py`); **Units** (mm of water; 1 mm over 1 m² is 1 litre; `litres`, `L/h`, minutes); **Formulas**, each with its FAO-56 source: Kc for a date (Eq. 66, `i = days since planting + 1`, at least 1; stages; `Kc_end` after the season), `ETc = Kc × ET0` (Eq. 56), `TAW = soil_mm_per_m × Zr` (Eq. 82), `RAW = p × TAW` (Eq. 83), the daily rule exactly as in the design's "One day" section (rain first, irrigate that morning when `Dr_after_rain + ETc > RAW`, `irrigation_mm = Dr_after_rain`, `Dr_end` never above `TAW`, `bucket_mm = TAW − Dr_end`, day 1 starts with `Dr = 0`), `litres = irrigation_mm × area_m2`, `run_minutes = irrigation_mm × row_spacing_m × emitter_spacing_m ÷ flow_lph × 60`; **Approximations stated** (single Kc; no climate adjustment; no `fw` adjustment of `Kc_ini`; no efficiency factor; all rain counts; each emitter serves `row × emitter spacing`); **Crop values** (point to `crops.py`; mark them provisional pending the instructor); **Three hand-calculated cases** (to be filled in Step 4).
- [ ] **Step 2: Define the three input sets** in `SKILL.md` and `tests/cases.py` (inputs only; the learner calculates the results). All three: stale `false`, no efficiency factor, forecast of 7 days from the start date, crop table as in Global Constraints.
  - **Case 1, tomato mid-season with irrigation.** Soil sand (83 mm/m). Planting 2026-08-01, start date 2026-10-20 (day index 81, mid stage). Area 1000 m², row spacing 1.5 m, emitter spacing 0.4 m, flow 2.0 L/h. ET0 per day: 5.0, 5.5, 6.0, 6.0, 5.5, 5.0, 5.0. Rain 0 every day.
  - **Case 2, rain delays an irrigation.** Same as Case 1, but rain 10.0 mm on day 3 and 0 on every other day.
  - **Case 3, bell pepper in the development stage.** Soil sand (83 mm/m). Planting 2026-09-20, start date 2026-10-25 (day index 36, development stage). Area 400 m², row spacing 1.2 m, emitter spacing 0.3 m, flow 2.0 L/h. ET0 4.0 every day, rain 0 every day.
- [ ] **Step 3: STOP and ask the learner** to calculate each case by hand, day by day, with the formulas in the skill: `kc`, `et0_mm`, `irrigation_mm`, `litres`, `run_minutes` and `bucket_mm` for the 7 days. The implementer does not calculate these numbers (the hand calculations are the independent check on the engine). If the learner asks, it may check their arithmetic or explain a formula.
- [ ] **Step 4: Record the learner's results** in the skill's third section and in `tests/cases.py` as `CASES: list[Case]` where `Case` is a dataclass with `name: str`, the inputs above (as `PlotInputs`-shaped plain values: `crop_id`, `soil_mm_per_m`, `planting_date`, `area_m2`, `row_spacing_m`, `emitter_spacing_m`, `emitter_flow_lph`, `et0` list, `rain` list, `start_date`), and `expected: list[dict]` with keys `kc`, `irrigation_mm`, `litres`, `run_minutes`, `bucket_mm` for each of the 7 days.
- [ ] **Step 5: Verify:** `SKILL.md` has valid frontmatter (`name`, `description`), every formula names its source, each case lists inputs and day-by-day results. No pytest test for this task (documentation and data).
- [ ] **Step 6: Commit** `.claude/skills/irrigation-calc-reference/` and `tests/cases.py`: "Add the irrigation-calc-reference skill and the hand-calculated cases".

---

### Task 3: `crops.py`

**Files:**
- Create: `crops.py`, `tests/test_crops.py`

**Interfaces:**
- Produces in `crops.py`:
  - `@dataclass(frozen=True) class Crop: kc_ini: float; kc_mid: float; kc_end: float; stage_days: tuple[int, int, int, int]; root_depth_m: float; p: float`.
  - `CROPS: dict[str, Crop]` with keys `"tomato"` and `"bell-pepper"` and the values in Global Constraints.
  - `class UnknownCrop(Exception)` with attribute `crop_id: str`.
  - `get_crop(crop_id: str) -> Crop` (raises `UnknownCrop`).
- Each number has a comment citing its FAO-56 table (Table 12 for Kc, Table 11 for stage lengths, Table 22 for `Zr` and `p`) and, where the choice is the learner's or provisional, saying so.

- [ ] **Step 1: Write the failing tests:** `test_tomato_values` and `test_bell_pepper_values` (exact values from Global Constraints), `test_stage_lengths_are_positive_integers`, `test_kc_values_and_p_are_in_range` (all Kc > 0, `0.1 <= p <= 0.8`, `Zr > 0`), `test_unknown_crop_raises_with_its_id` (`get_crop("wheat")` raises `UnknownCrop`, `crop_id == "wheat"`), `test_crop_is_immutable`.
- [ ] **Step 2: Run them.** Expected: FAIL (no `crops` module).
- [ ] **Step 3: Implement `crops.py`** with the table and the citation comments.
- [ ] **Step 4: Run `uv run pytest -q`.** Expected: all pass.
- [ ] **Step 5: Commit:** "Add the crop table with FAO-56 citations".

---

### Task 4: `engine.py`

**Files:**
- Create: `engine.py`, `tests/test_engine.py`

**Interfaces:**
- Consumes: `crops.Crop`; `tests/cases.py` (`CASES`, from Task 2).
- Produces in `engine.py` (all floats, no rounding):
  - `@dataclass(frozen=True) class PlotInputs: crop: Crop; planting_date: date; area_m2: float; row_spacing_m: float; emitter_spacing_m: float; emitter_flow_lph: float; soil_mm_per_m: float`.
  - `@dataclass(frozen=True) class ForecastDay: date: date; et0_mm: float; rain_mm: float; stale: bool`.
  - `@dataclass(frozen=True) class PlanDay: date: date; et0_mm: float; kc: float; irrigation_mm: float; litres: float; run_minutes: float; stale: bool; bucket_mm: float`.
  - `kc_for(crop: Crop, planting_date: date, day: date) -> float`.
  - `plan(plot: PlotInputs, forecast: Sequence[ForecastDay]) -> list[PlanDay]` (one `PlanDay` per forecast day, in order; the bucket starts full).

- [ ] **Step 1: Write the failing tests in `tests/test_engine.py`:**
  - Kc: `test_kc_on_the_planting_day_is_the_initial_value`; `test_kc_boundaries` parametrised for each crop over the day indices `1, L_ini, L_ini+1, L_ini+L_dev, L_ini+L_dev+1, L_ini+L_dev+L_mid, L_ini+L_dev+L_mid+1, total, total+1, total+500` with the expected value written out (initial value, linear interpolation between stage values, mid value, linear down to end value, end value); `test_kc_is_linear_inside_development` (a day halfway gives the mean of `Kc_ini` and `Kc_mid`); `test_planting_date_after_the_day_counts_as_day_one`; `test_plot_past_its_season_keeps_kc_end`.
  - Bucket rule: `test_assignment_example_irrigates_on_day_six` (a synthetic crop with `Kc = 1`, `Zr × soil` giving `TAW = 70`, `p = 0.5`, ET0 7 mm a day, no rain: the level is 63, 56, 49, 42, 35 on days 1 to 5 with `irrigation_mm = 0`, and day 6 irrigates 35 mm); `test_exactly_at_the_threshold_does_not_irrigate`; `test_bucket_starts_full_on_day_one`; `test_rain_reduces_the_depletion`; `test_rain_larger_than_the_depletion_does_not_overfill` (depletion floors at 0, bucket never above `TAW`); `test_irrigation_never_exceeds_the_depletion` (every day: `irrigation_mm <= Dr_after_rain`); `test_depletion_never_exceeds_taw` (a huge ET0 day: `bucket_mm >= 0`); `test_day_after_irrigation_starts_from_the_etc` (`bucket_mm = TAW − ETc` on an irrigation day); `test_stale_flag_is_copied_per_day`.
  - From depth to minutes: `test_litres_are_depth_times_area`; `test_run_minutes_use_row_and_emitter_spacing_and_flow` (a hand-checkable example: need 10 mm, row 1.5, emitter spacing 0.4, flow 2.0 → `10 × 1.5 × 0.4 ÷ 2.0 × 60 = 180` minutes); `test_no_irrigation_means_zero_litres_and_minutes`; `test_area_does_not_change_the_run_minutes` (area doubled: litres double, minutes unchanged).
  - Hand cases: parametrised `test_hand_calculated_case` over `CASES`: every day's `kc`, `irrigation_mm`, `litres`, `run_minutes`, `bucket_mm` equal the learner's expected values within `pytest.approx(rel=0.005, abs=0.01)`.
  - Purity: `test_engine_does_no_io` (`engine.py` source contains no `httpx`, `open(`, `datetime.now` or `date.today`).
- [ ] **Step 2: Run them.** Expected: FAIL (no `engine` module).
- [ ] **Step 3: Implement `engine.py`** exactly as the skill's formulas. Comment each step with its FAO-56 source and explain the bucket to a C# reader (a variable that fills with rain, drains with crop use, and is topped up by irrigation).
- [ ] **Step 4: Run `uv run pytest -q`.** Expected: all pass. If a hand case differs from the engine by more than 0.5%, do not change either to match: report the difference to the learner, and find out whether the hand calculation or the skill's formula is wrong.
- [ ] **Step 5: Commit:** "Add the irrigation engine".

---

### Task 5: `upstream.py` and the fakes

**Files:**
- Create: `upstream.py`, `tests/fakes.py`, `tests/test_upstream.py`

**Interfaces:**
- Consumes: `config.Settings`; `engine.ForecastDay`.
- Produces in `upstream.py`:
  - `class UpstreamError(Exception)` with attributes `service: str` (`"registry-service"` or `"weather-service"`) and `reason: str`; `str(error)` is `f"{service} is unavailable: {reason}"`. The reason is a short fixed phrase, an exception class name, or `status <code>`; never a URL.
  - `class PlotNotFound(Exception)`.
  - `@dataclass(frozen=True) class PlotData: crop_id: str; planting_date: date; soil_id: str; area_m2: float; row_spacing_m: float; emitter_spacing_m: float; emitter_id: str; lat: float; lon: float`.
  - `@dataclass(frozen=True) class Forecast: stale: bool; days: list[ForecastDay]`.
  - `class Upstream`: `__init__(self, settings: Settings, client: httpx.AsyncClient)`; `async get_plot(self, plot_id: str) -> PlotData` (raises `PlotNotFound` when the registry answers `404`, `UpstreamError("registry-service", ...)` otherwise); `async get_soil_mm_per_m(self, soil_id: str) -> float`; `async get_emitter_flow_lph(self, emitter_id: str) -> float` (both raise `UpstreamError("registry-service", ...)` for any failure, including `404`); `async get_forecast(self, lat: float, lon: float, days: int) -> Forecast` (raises `UpstreamError("weather-service", ...)`).
- Produces in `tests/fakes.py`: `plot_json(**overrides) -> dict` (the registry's "North block": id `c8f3d1b0-4d2e-5a1b-8b22-1d6e3f702002`, tomato, planted `2026-03-01`, loam, area 1000, spacings 1.5 and 0.4, emitter `dripnet-pc-1.0`, lat 31.25, lon 34.79); `soil_json(mm=175)`, `emitter_json(flow=1.0)`, `forecast_json(start: date, days: int = 7, et0: float = 3.0, rain: float = 0.0, stale: bool = False) -> dict` (the weather service's response shape); `class FakeUpstreams` with attributes `plot`, `soil`, `emitter`, `forecast` (each a step: a dict answers `200`, an `int` answers that status with body `{}`, an `Exception` instance is raised, `"not-json"` answers `200` with a text body; defaults are valid answers), `calls: list[httpx.Request]`, `transport: httpx.MockTransport`, `client() -> httpx.AsyncClient`. The transport routes by URL: host `registry.test` paths `/v1/plots/{id}`, `/v1/soils/{id}`, `/v1/emitters/{id}`; host `weather.test` path `/v1/forecast`. An `asyncio` delay option is not needed.

- [ ] **Step 1: Write `tests/fakes.py`** as above (helpers, no test of its own).
- [ ] **Step 2: Write the failing tests in `tests/test_upstream.py`** (anyio):
  - Happy paths: `test_get_plot_returns_the_plot_fields`, `test_get_soil_and_emitter_values`, `test_get_forecast_returns_days_and_stale_flag`; `test_forecast_request_has_lat_lon_and_days` (captured query parameters).
  - Registry failures (parametrised over `get_plot`, `get_soil_mm_per_m`, `get_emitter_flow_lph`): status 500, 503, `httpx.ConnectTimeout`, `httpx.ConnectError`, `"not-json"` each raise `UpstreamError` with `service == "registry-service"`; `test_plot_404_is_plot_not_found`; `test_soil_404_is_an_upstream_error` and `test_emitter_404_is_an_upstream_error` (the registry should know every id a plot refers to).
  - Invalid registry bodies (parametrised): plot with a missing field, `area_m2` 0 or negative or a string or a boolean, `planting_date` not an ISO date, `lat` 91, `lon` 181, `row_spacing_m` `null`; soil `available_water_mm_per_m` 0 or `null`; emitter `flow_lph` 0 or negative → `UpstreamError("registry-service")`.
  - Weather failures: status 500, 503, 422, `httpx.ConnectTimeout`, `"not-json"` → `UpstreamError` with `service == "weather-service"`.
  - Invalid weather bodies (parametrised): `days` empty; fewer days than requested; more days than requested; a `null` `et0_mm`; a negative `rain_mm`; a boolean value; `nan`; dates not consecutive; `stale` missing or not a boolean; not an object → `UpstreamError("weather-service")`.
  - `test_error_message_has_no_url` (`"://"` not in `str(error)`).
- [ ] **Step 3: Run them.** Expected: FAIL (no `upstream` module).
- [ ] **Step 4: Implement `upstream.py`.** The weather and registry timeouts from settings go in `httpx.Timeout(...)` per request. Validation is explicit, with `bool` checked before numbers, as in `services/weather-service/provider.py`.
- [ ] **Step 5: Run `uv run pytest -q`.** Expected: all pass.
- [ ] **Step 6: Commit:** "Add the registry and weather clients with strict validation".

---

### Task 6: `planner.py`, `errors.py`, `main.py`

**Files:**
- Create: `planner.py`, `errors.py`, `main.py`, `tests/test_planner.py`, `tests/test_api.py`

**Interfaces:**
- Consumes: `Upstream`, `UpstreamError`, `PlotNotFound`, `PlotData`, `Forecast` (Task 5); `crops.get_crop`, `UnknownCrop`; `engine.plan`, `PlotInputs`.
- Produces:
  - `errors.add_error_handlers(app: FastAPI) -> None`: adapted from `services/weather-service/errors.py`; `422` and `400` and `405` → `VALIDATION`, `404` → `NOT_FOUND`, `503` → `UPSTREAM_UNAVAILABLE`.
  - `planner.build_plan(upstream: Upstream, plot_id: str, days: int) -> PlanOut` (async). Order: `get_plot`; then `get_crop` (an `UnknownCrop` becomes `HTTPException(422)` with the crop named); then `asyncio.gather(..., return_exceptions=True)` for soil, emitter and forecast; if any failed, re-raise in this order: soil, emitter, forecast (so the registry is reported before the weather service); then `engine.plan` and rounding.
  - Pydantic models `PlanDayOut` (`date`, `et0_mm`, `kc`, `litres`, `run_minutes`, `stale`, `bucket_mm`; no `irrigation_mm`) and `PlanOut` (`plot_id: str`, `days: list[PlanDayOut]`), rounding as in Global Constraints.
  - `main.create_app(settings: Settings | None = None, transport: httpx.AsyncBaseTransport | None = None) -> FastAPI` (lifespan builds settings via `get_settings()` when none given, so a missing variable fails at startup; one `httpx.AsyncClient(transport=transport)`, closed on shutdown); `main.app = create_app()`. Routes: `GET /health` → `{"status": "ok"}`; `GET /v1/plots/{plot_id}/plan` with query `days: int` in 1..7, default 7. `UpstreamError` → `HTTPException(503, detail=str(error))`.

- [ ] **Step 1: Write the failing tests in `tests/test_planner.py`** (anyio, `FakeUpstreams`): `test_plan_matches_the_engine` (loam, Kc end, 7 days: day 1 `kc 0.8`, `bucket_mm` equals `175 × 0.7 − 3.0 × 0.8` to 2 decimals), `test_response_is_rounded_only_at_the_end` (a value with many decimals rounds to 2 for mm and 3 for `kc`, and the day-by-day state still uses the unrounded numbers), `test_stale_forecast_marks_every_day_stale`, `test_calls_soil_emitter_and_forecast_after_the_plot` (the forecast request uses the plot's `lat` and `lon`; the plot request comes first), `test_unknown_crop_is_a_422_that_names_it` (plot with `crop_id` `"wheat"`), `test_registry_failure_is_reported_before_weather_failure` (soil answers 500 and forecast answers 500: the `detail` names `registry-service`).
- [ ] **Step 2: Write the failing tests in `tests/test_api.py`** (`TestClient(create_app(make_settings(), fake.transport))` as a context manager): `test_plan_has_the_documented_shape` (top level keys exactly `plot_id`, `days`; per day exactly the 7 fields); `test_days_default_is_seven`; `test_days_can_be_one_to_seven`; parametrised `test_bad_days_is_422_validation` (`0`, `8`, `abc`, `3.5`, empty, `-1`); `test_unknown_plot_is_404_not_found`; `test_malformed_plot_id_is_404` (the registry answers 404 for it); `test_registry_down_is_503_upstream_unavailable_naming_it` (plot answers 500; and a timeout; and a non-JSON body); `test_weather_down_is_503_upstream_unavailable_naming_it` (status 503, a timeout, a non-JSON body, an empty `days`, `null` values); `test_never_a_plan_of_zeros_when_weather_fails` (the response has no `days` key on every failure); `test_stale_forecast_still_gives_a_plan` (200, every `stale` true); `test_registry_failure_beats_weather_failure_in_the_detail`; `test_problem_json_content_type_on_every_error`; `test_health_ok_and_calls_nothing`; `test_unknown_route_404_not_found`; `test_wrong_method_405`; `test_app_refuses_to_start_without_settings` (empty environment: `RuntimeError` naming `REGISTRY_URL`).
- [ ] **Step 3: Run them.** Expected: FAIL (no `planner`, `main`).
- [ ] **Step 4: Implement `errors.py`, `planner.py`, `main.py`.** Add a one-paragraph explanation for the learner of why the three upstream calls run together (`asyncio.gather`) and what `return_exceptions=True` does.
- [ ] **Step 5: Run `uv run pytest -q`.** Expected: all pass. Run `uv run pytest -q -W error`; expected: clean.
- [ ] **Step 6: Commit:** "Add the plan route, health route and problem+json errors".

---

### Task 7: README and a real three-service smoke check

**Files:**
- Modify: `services/planner-service/README.md`

- [ ] **Step 1: Write the README:** what the planner does and its calling order; the endpoint with the response shape and an example (the registry's "North block" with real numbers from Step 3); the error table (422, 404, 503 with the service named); each calculation step in plain words with its FAO-56 source, pointing to the `irrigation-calc-reference` skill; the crop table and which values are provisional pending the instructor; the stated approximations (single Kc, no climate adjustment, no `fw` adjustment of the initial Kc, no efficiency factor, all rain counts, each emitter serves `row × emitter spacing`, a plot past its season keeps the last Kc, the bucket starts full, the plan is only as good as those assumptions); `.env` variables (with a note that the weather timeout must exceed the weather service's worst case); a file table; how to run the tests; the optional Mermaid diagram (frontend, planner, registry, weather, and the failure branches).
- [ ] **Step 2: Real smoke check, no `.env` needed.** Start three servers in the background with variables passed inline (never reading a `.env`): the registry on a temporary SQLite database seeded with `seed.py` (`DATABASE_URL=sqlite:///<scratchpad>/smoke.db`, port 8000, from `services/registry-service`), the weather service on port 8001 with the `.env.example` values, the planner on port 8002 with `REGISTRY_URL=http://127.0.0.1:8000 WEATHER_URL=http://127.0.0.1:8001` and the timeouts from `.env.example`. Request `curl "http://127.0.0.1:8002/v1/plots/c8f3d1b0-4d2e-5a1b-8b22-1d6e3f702002/plan?days=7"`. Expected: `200`, 7 days from today's date, `kc` 0.8 (the plot is past its season), `bucket_mm` near 122.5 minus the day's `ETc`, `stale` false. Then: `?days=8` (422), an unknown id (404), and the weather service stopped (503 naming `weather-service`). Stop the servers by the process ids you started. Report the numbers faithfully; if a service cannot start or the provider is unreachable, say so.
- [ ] **Step 3: Put the real response in the README example,** and fix any difference between the README and the behaviour in the README.
- [ ] **Step 4: Commit:** "Document planner-service".

---

## Self-Review

- **Spec coverage:** FR-2.9 and the route (Task 6); FR-2.10 fields and rounding (Tasks 4, 6); FR-2.11 numbers from the skill (Tasks 2, 4); FR-2.12 `422` and `404` (Task 6); FR-2.13 stale per day (Tasks 5, 6); FR-2.14 `503` naming the service, never zeros (Tasks 5, 6); accuracy against the hand cases, our own 0.5% standard (Tasks 2, 4); config and `.env.example` (Task 1); the skill (Task 2); README, optional diagram, approximations (Task 7); `/health` (Task 6); the crop table with citations (Task 3).
- **Names:** `Crop`, `CROPS`, `get_crop`, `UnknownCrop`, `PlotInputs`, `ForecastDay`, `PlanDay`, `kc_for`, `plan`, `Upstream`, `UpstreamError`, `PlotNotFound`, `PlotData`, `Forecast`, `FakeUpstreams`, `build_plan`, `PlanOut`, `create_app`, `make_settings` are used the same way wherever they appear.
- **Not in the plan on purpose:** retries or caching of upstream answers, a performance check, the dual coefficient, an efficiency factor, any `fw` adjustment.
- **Decisions awaiting the learner's confirmation** (propose wording, wait, then write to `docs/judgment-log-p2.md`): the five listed at the end of the design. Several values are provisional pending the instructor's answers (`docs/p2-planner-questions-for-instructor.md`).
