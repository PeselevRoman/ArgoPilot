# planner-service: design

Decisions are recorded only in `docs/judgment-log-p2.md`. This file describes the design and does not restate the reasoning. Already logged: "The planner uses the single crop coefficient (FAO-56 Chapter 6), not the dual one".

Source of requirements: `tasks/p2.md`, section "The `planner-service`" (FR-2.9 to FR-2.14, NFR-2.5) and "Global configurations". Source of domain knowledge: `services/planner-service/docs/research/fao56.md` (FAO-56 Ch. 5, 6, 8, Annex 8; values spot-checked against fao.org on 2026-11-16).

**Provisional defaults.** Several values below are marked *(provisional)*. They are the defaults in `docs/p2-planner-questions-for-instructor.md` and may change when the instructor answers. They are built as single named values so a change is a one-line edit.

## Intent

Answer "should I water this plot today, and for how many minutes?" for the next 1 to 7 days. The planner turns a plot (from the registry) and a forecast (from the weather service) into a day-by-day plan: the crop's water use, the state of the soil bucket, and when and how long to run the drip system. Every irrigation number comes from one calculation module that follows the `irrigation-calc-reference` skill. No AI model computes or adjusts a number (CLAUDE.md rule 12).

## Goals

- `GET /v1/plots/{id}/plan?days={days}` as in FR-2.9 to FR-2.14, with the response below.
- `GET /health` returning `{"status": "ok"}` (the frontend status line needs it, FR-2.19). It does not call other services.
- Numbers accurate to within 0.5% of the hand-calculated cases (NFR-2.5).
- When the registry or the weather service fails, a clear `503 UPSTREAM_UNAVAILABLE` naming the service. Never a plan of zeros.
- The `irrigation-calc-reference` skill: formulas, units, three hand-calculated cases, pointing to `fao56.md`.

## Non-goals and anti-goals

- No database, no stored plans, no irrigation history, no caching of upstream answers.
- The dual coefficient and everything in FAO-56 Chapter 7 (soil-evaporation layer, wind and humidity corrections of Kc) are out of scope.
- No retries and no stale memory on the planner's own upstream calls. The weather service already retries and serves stale.
- Anti-goals: a plan built on numbers the upstream services did not give; a missing day filled with a default; any number produced or adjusted outside `engine.py`.
- No performance requirement is stated for the planner, so there is no performance check.

## Approaches considered

- **Engine structure.** A pure calculation module (`engine.py`, no network, no clock) wrapped by a thin service layer. Chosen: it is testable against hand-calculated cases without fakes, and rule 12 has one place to point at.
- **Where the crop numbers live.** A) a Python module `crops.py` with a cited source beside each number (chosen by the learner); B) a JSON or YAML data file; C) `.env` variables. Crop coefficients are domain knowledge, not environment configuration, and each needs a citation.
- **Number type.** `float` (chosen by the learner). The 0.5% tolerance is far wider than float error. Full precision inside, rounding only in the response.

## Behavior

| Situation | Answer |
|---|---|
| `days` not an integer from 1 to 7 | `422`, `code: VALIDATION` (default `days` is 7) |
| Registry answers `404` for the plot (including a malformed id) | `404`, `code: NOT_FOUND` |
| The plot's crop has no table in `crops.py` | `422`, `code: VALIDATION`, the `detail` names the crop (unreachable today: the registry catalogue holds two crops) |
| Registry or weather service unreachable, timed out, answers a non-2xx status, or answers a body that is invalid | `503`, `code: UPSTREAM_UNAVAILABLE`, the `detail` names the service |
| Weather service answers with fewer or different days than requested | the same `503` naming the weather service (the planner never pads a day) |
| Forecast is stale | the plan is returned, with `stale: true` on every day (FR-2.13) |
| Everything works | `200` with the plan |

### Upstream calls

1. `GET {REGISTRY_URL}/v1/plots/{id}` (needs `crop_id`, `planting_date`, `soil_id`, `area_m2`, `row_spacing_m`, `emitter_spacing_m`, `emitter_id`, `lat`, `lon`).
2. Then together: `GET {REGISTRY_URL}/v1/soils/{soil_id}` (`available_water_mm_per_m`), `GET {REGISTRY_URL}/v1/emitters/{emitter_id}` (`flow_lph`), and `GET {WEATHER_URL}/v1/forecast?lat&lon&days` (the weather service needs the plot's coordinates, so it waits for step 1).

Every upstream answer is validated like the weather service validates its provider: right types, finite, positive where required, the right number of consecutive dates. An answer that fails validation counts as that service being unavailable. The planner reads only the fields it needs. It does not retry.

## The calculation (`engine.py`)

Written in the skill `irrigation-calc-reference`; this section is the summary. All sources are in `fao56.md`.

**Inputs.** From the crop table (`crops.py`): `Kc_ini`, `Kc_mid`, `Kc_end`, stage lengths `L_ini`, `L_dev`, `L_mid`, `L_late` (days), root depth `Zr` (m), depletion fraction `p`. From the plot and its soil and emitter: `planting_date`, area, spacings, `soil_mm_per_m`, `flow_lph`. From the forecast, per day: date, `ET0`, `rain`, stale flag.

**Kc for a date** (FAO-56 Ch. 6, Eq. 66, single coefficient). `i = (date − planting_date) in days + 1`, never less than 1. Constant `Kc_ini` while `i ≤ L_ini`; straight line from `Kc_ini` to `Kc_mid` across the development stage; constant `Kc_mid` through the mid stage; straight line from `Kc_mid` to `Kc_end` across the late stage; `Kc_end` for every later day (a plot past its season keeps the last Kc, *provisional*). No climate adjustment of `Kc_mid` and `Kc_end` (needs wind and humidity), and no wetted-fraction adjustment of `Kc_ini` *(provisional)*; both are documented approximations.

**Crop water use.** `ETc = Kc × ET0` (Ch. 5, Eq. 56).

**The bucket** (Ch. 8, Eq. 82, 83, 85). `TAW = soil_mm_per_m × Zr` (mm). `RAW = p × TAW`. The state is the depletion `Dr` (mm below full). Day 1 starts with `Dr = 0` *(provisional)*.

**One day**, with `Dr_start` carried from the day before:
1. Rain: `Dr_after_rain = max(0, Dr_start − rain)`. Water above full is lost. All forecast rain counts, with no runoff *(provisional)*.
2. If `Dr_after_rain + ETc > RAW` the level would fall below the threshold today, so irrigate in the morning: `need_mm = Dr_after_rain` (refill exactly the depletion, never more, Ch. 8 `I ≤ Dr`); `Dr_end = ETc`. Otherwise `need_mm = 0` and `Dr_end = Dr_after_rain + ETc`. Exactly at the threshold does not trigger.
3. `Dr_end` never exceeds `TAW` (Eq. 86). The level reported is `bucket_mm = TAW − Dr_end`. `Dr_end` becomes the next day's `Dr_start`.

**From depth to minutes.** `litres = need_mm × area_m2` (1 mm over 1 m² is 1 litre). Each emitter serves `row_spacing_m × emitter_spacing_m` m² (this layout assumption is the design's own, not FAO-56's; *provisional*), so `run_minutes = need_mm × row_spacing_m × emitter_spacing_m ÷ flow_lph × 60` (the area cancels). No application-efficiency factor *(provisional)*.

**Rounding.** Everything is computed in full float precision; only the response rounds: 2 decimals for `et0_mm`, `need_mm`, `litres`, `run_minutes`, `bucket_mm`; 3 decimals for `kc`.

### Crop table (`crops.py`, *provisional* values, each cited)

| | `Kc_ini` | `Kc_mid` | `Kc_end` | stages (days) | `Zr` | `p` |
|---|---|---|---|---|---|---|
| `tomato` | 0.6 | 1.15 | 0.80 (middle of 0.70-0.90) | 30 / 40 / 45 / 30 (Table 11, Mediterranean) | 0.7 m | 0.40 |
| `bell-pepper` | 0.6 | 1.05 | 0.90 | 30 / 35 / 40 / 20 (Table 11, Europe and Mediterranean; the "25/30" read as 30) | 0.5 m | 0.30 |

Kc from Table 12 (Ch. 6; `Kc_ini` 0.6 is the Solanum group value), `Zr` and `p` from Table 22 (Ch. 8; the lower root depth, which the table's note recommends for scheduling). FAO's ETc adjustment of `p` and the soil-texture adjustment are not applied.

## Response (FR-2.10)

Example for the registry's "North block" (tomato, loam: `TAW = 175 × 0.7 = 122.5 mm`; planted 2026-03-01, so past its season and `Kc = 0.80`; bucket full at the start):

```json
{
  "plot_id": "c8f3d1b0-4d2e-5a1b-8b22-1d6e3f702002",
  "days": [
    { "date": "2026-11-16", "et0_mm": 2.71, "kc": 0.8, "need_mm": 0.0,
      "litres": 0.0, "run_minutes": 0.0, "stale": false, "bucket_mm": 120.33 },
    "... up to 7 days ..."
  ]
}
```

`need_mm` is the irrigation depth applied that day, 0 on days without irrigation (*provisional*, the instructor's answer may redefine it). `bucket_mm` is the water in the root zone at the end of the day. `run_minutes: 0` means no irrigation. No other fields (CLAUDE.md rule 6).

## Configuration (`config.py`, pydantic-settings, `.env`)

All required, no defaults in code, checked at startup (same rules as the weather service, including no `nan` or `inf`): `REGISTRY_URL`, `WEATHER_URL`, `REGISTRY_TIMEOUT_SECONDS`, `WEATHER_TIMEOUT_SECONDS`. The weather timeout must be longer than the weather service's worst case (its README, "How long can one request take?"), or the planner gives up before the weather service can return its stale answer. `.env.example` lists all with safe values. Port 8002.

## Components

`services/planner-service/`, own `.venv`, `pyproject.toml`, `README.md`, `tests/`, and `docs/research/fao56.md` (already there):

- `config.py`: settings.
- `errors.py`: `application/problem+json` for `VALIDATION`, `NOT_FOUND`, `UPSTREAM_UNAVAILABLE`. Copied from the weather service's, not imported.
- `crops.py`: the crop table above, as typed constants with citations.
- `engine.py`: the pure calculation. No network, no clock, no I/O.
- `upstream.py`: the two clients (registry, weather): the calls, the validation, the errors that name the service.
- `planner.py`: ties them together: calls, engine, response shape.
- `main.py`: app, routes `/v1/plots/{id}/plan` and `/health`.
- `.claude/skills/irrigation-calc-reference/SKILL.md`: the knowledge skill.

## Order of work

1. Write the skill from the research and the defaults. You check the formulas and calculate three cases by hand: (1) a tomato plot in mid-season with an irrigation, including litres and minutes; (2) a case where rain cancels an irrigation; (3) a pepper plot in the development stage, on sandy soil, with a Kc between stages. The values go into the skill and the tests.
2. The engine, test-first against those cases and against the assignment's 70 mm example (a bucket losing 7 mm a day is exactly half after 5 days and irrigates on day 6), and FAO-56 Example 37's bucket numbers.
3. The upstream clients, the service layer and the routes.
4. README with the example response, the stated approximations, and the optional sequence diagram.

## Testing

No real network and no real clock. Upstream services are fakes behind `httpx.MockTransport`.

- **Engine (unit):** the three hand cases within 0.5%; Kc at every stage boundary and one day either side; a plot past its season; day 1 with and without rain; exactly at the threshold; rain larger than the depletion; a large ETc that would exceed `TAW`; rounding only at output; irrigation depth never above the depletion.
- **Upstream clients:** valid answer; timeout; connection error; each non-2xx status; non-JSON; wrong types; missing fields; a non-finite or negative number; fewer or non-consecutive forecast days; the `detail` names the right service.
- **API:** `days` bounds and default; unknown plot; malformed plot id; the unsupported-crop case; registry down; weather down; weather slow; stale forecast gives `stale: true` on every day; the answer never contains a plan of zeros when an upstream fails; only the spec's fields in the response.
- **Config:** a missing or invalid variable fails at startup.

## Left to the builder

Names inside the files, the `detail` wording, how to share the HTTP client, the structure of the validation helpers, the README text.

## Decisions to log (pending your confirmation)

1. Crop numbers live in a cited Python module, not a data file or `.env`.
2. Floats throughout, rounding only in the response (2 decimals for mm, litres and minutes; 3 for Kc).
3. The daily rule: irrigate on the morning of day D when the level would fall below the threshold that day, refilling exactly the depletion at that moment; the bucket starts full; rain counts fully.
4. The planner treats any invalid upstream answer as that service being unavailable, and never pads a missing forecast day.
5. The provisional crop values and their sources (after the instructor answers).
