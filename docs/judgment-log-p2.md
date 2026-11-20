# Judgment log: P2

Decisions for the second assignment (`tasks/p2.md`). Decisions from P1 are in [`judgment-log.md`](judgment-log.md). Where a P2 decision overrides a P1 one, the entry says so.

## Each assignment gets its own judgment log

- **Question:** P2 adds many decisions on top of P1's 40 or so entries. Should they go in the same `judgment-log.md`, or in a new file?
- **Suggested:** None. This was the learner's own proposal.
- **Decision:** P2 decisions go in `docs/judgment-log-p2.md`. `docs/judgment-log.md` stays as the record of P1 and is no longer added to. Later assignments follow the same pattern.
- **Why:** Each assignment's decisions are easy to find and review on their own, and the P1 record stays as it was when that assignment was finished. Trade-off: the decisions are spread over several files, so a P2 decision that overrides a P1 one must say so in its entry, and `CLAUDE.md` must tell the assistant which files to check.

## P2 adds a fifth error code, UPSTREAM_UNAVAILABLE

- **Question:** P1 allowed four error codes. P2 requires `UPSTREAM_UNAVAILABLE` when the planner's call to the registry or weather service fails. Does the four-code rule still stand?
- **Suggested:** Treat the newer assignment as overriding the older one, so there are five codes. Labelled as personal judgment.
- **Decision:** Five codes: `VALIDATION`, `NOT_FOUND`, `CONFLICT`, `UNAVAILABLE`, `UPSTREAM_UNAVAILABLE`. A service uses `UNAVAILABLE` when its own dependency fails, such as its database or its weather provider, and `UPSTREAM_UNAVAILABLE` when another AgroPilot service it calls has failed. The P1 mappings for `400` and `405` stay as they are.
- **Why:** The P2 spec asks for the new code by name, and the planner needs to tell the client that the failure is in another service. Where P2 and P1 disagree, the newer assignment wins.

## The registry's one-command setup is a Python seed script

- **Question:** FR-2.2 needs one command that builds an empty PostgreSQL database and loads the 15 seed rows. How?
- **Suggested:** A Python script (`seed.py`) using SQLAlchemy, over `psql` with SQL files or Alembic. Labelled as personal judgment.
- **Decision:** `uv run python seed.py` picks the schema file for the engine, creates the tables and inserts the rows. It stops with an error if the tables already exist, and never drops data.
- **Why:** The same command works on SQLite and PostgreSQL (NFR-2.1), needs no `psql`, and can be tested in pytest. Trade-off: the seed rows now live in a second place besides `seed_registry.sh`. Alembic is the standard tool when a schema keeps evolving, and P2 does not need it.

## PostgreSQL performance data lives in a separate `registry_perf` database, guarded by name

- **Question:** NFR-2.2 needs p95 on PostgreSQL with the 10,000-plot dataset. Where does that data go?
- **Suggested:** A separate database, rebuilt on every run, and refused unless its name contains `perf`. Labelled as personal judgment.
- **Decision:** `perf/seed_perf_db.py` drops and recreates the tables of a PostgreSQL target only if the database name contains `perf`. `registry` and `registry_test` are refused. An empty target is refused too.
- **Why:** The perf run must not touch real or test data, and a name check is a cheap guard against dropping the wrong database. Trade-off: one more database to create by hand.

## Stale forecasts are served for up to 24 hours

- **Question:** How old can a forecast be before the weather service stops serving it as stale?
- **Suggested:** 24 hours. Labelled as personal judgment; no authoritative source was found.
- **Decision:** After 3 hours a forecast is stale. If the provider fails, the service serves it with `stale: true` until it is 24 hours old, and then answers `503`. The limit is `MAX_STALE_HOURS` in `.env`.
- **Why:** 24 hours covers an overnight outage, and near-term forecasts keep most of their value for a day. Longer limits risk watering on old rain information. Trade-off: after 24 hours the grower gets no plan.

## A forecast cell is a 0.1° square; the provider is asked for its centre

- **Question:** FR-2.5 says two points in the same 0.1° grid cell share one forecast. Which points belong to a cell, which point do we ask the provider about, and which coordinates does the answer show?
- **Suggested:** Round down to the tenth, ask for the cell centre, echo the requested point. Labelled as personal judgment.
- **Decision:** A cell is found by rounding each coordinate down to 0.1°, so `31.3` belongs to cell `31.3`, and `-0.05` to the cell just below zero. The calculation is exact on the decimal text of the number, not on floating-point arithmetic. The provider is asked for the cell's centre (cell origin plus 0.05°), clamped into -90..90 and -180..180, so `lat=90` or `lon=180` does not send an invalid request. The response shows the coordinates that were requested, not the cell's.
- **Why:** The centre represents every point in the cell equally, so all of them get the same numbers whichever one asked first. Rounding down gives each point exactly one cell, and the exact decimal arithmetic avoids float errors at the cell edges. Without the clamp, the top edge of the map would fail with a provider error. Trade-off: a point up to about 0.07° away from the centre gets the centre's forecast, which is small compared to the provider's own grid. The response's `lat`/`lon` differ from the forecast's true position, but they match the assignment's example.

## Nine days are fetched and kept; "today" is the local date at the point

- **Question:** The planner asks for 1 to 7 days starting today. A cached forecast gets older, and the provider can fail. How many days do we fetch, and what does "today" mean?
- **Suggested:** Always fetch 9 days, whatever was asked. Take "today" from the local time at the point. Labelled as personal judgment.
- **Decision:** The service always asks the provider for 9 days (`forecast_days=9`) and keeps all of them. The answer takes the next `days` days starting from today and drops days already past. "Today" is the local date at the point: the service asks for `timezone=auto`, keeps the provider's UTC offset with the cached forecast, and works out today from the clock plus that offset, so it also works while the provider is down. A stale forecast that no longer has enough real days from today is not served with fewer days (that would be a shorter answer than asked for). It counts as unusable, and the answer is `503`.
- **Why:** An entry can be served for up to 24 hours. By then at most one day has passed, so 7 requested plus 1 dropped is 8, and the 9th is a safety margin. Fetching a fixed size means one cache entry serves every `days` value from 1 to 7. Local time is what a grower means by "today", and a UTC date would be a day off for part of the day in many places. Trade-off: the later days of a 9-day forecast are less reliable, but we only return the days that were asked for. The offset is taken from the time of the fetch, so a daylight-saving change within a day could shift "today" by an hour. That is too small to matter here.

## A provider answer must be strictly valid, or it counts as a failure

- **Question:** FR-2.6 lists some provider failures (timeout, error status, a body that is not JSON, a missing field), and FR-2.8 says the service never answers with numbers the provider did not give. What exactly makes a `200` answer unusable?
- **Suggested:** Check the answer strictly, and treat anything that fails a check as a provider failure, never repairing it. The checks go beyond the assignment's list. Labelled as personal judgment.
- **Decision:** An answer is used only if all of these hold:
  - it is a JSON object with the daily dates, ET0 and rain lists, all with exactly 9 entries;
  - the dates are real ISO dates, one day apart;
  - every value is a real number: not `null`, text, a boolean, `nan`, `inf` or a number too large to hold, and not negative;
  - both units say `mm`;
  - the UTC offset is a whole number within 18 hours of UTC.

  Any failed check is a provider failure: the service retries, then falls back to the stale forecast or answers `503`. It never replaces a bad value with a zero, a default or a neighbouring day.
- **Why:** A forecast of zeros looks like "no water needed", the worst bug in this system (FR-2.8). A missing number replaced by a zero, or numbers in the wrong unit, would be served as if the provider had given them. The unit and offset checks catch a provider that changes its format quietly, and the offset bound stops a wild value from breaking date calculations later. Trade-off: one bad value among 9 days throws away the whole answer, so a mostly good forecast is refused and we fall back to an older one. Accepting partial answers would be more forgiving but much harder to reason about. There is no upper limit on plausible ET0 or rain values: choosing one is an agronomy decision that needs a cited source.

## Concurrent requests for one cell share a single provider fetch and its outcome

- **Question:** When a cell's forecast expires, many requests can arrive at the same moment. Should each one call the provider, or should they share?
- **Suggested:** Share one fetch per cell, including its failure. Labelled as personal judgment.
- **Decision:** While a fetch for a cell is running, any other request for that cell waits for it instead of starting its own. When the fetch finishes, every waiting request gets the same outcome: a fresh forecast, the stale fallback, or `503`. The retries (1 attempt plus `PROVIDER_RETRIES`) run once for the whole group. A caller that disconnects does not stop the fetch the others are waiting for. The service does not remember failures: after a failed fetch finishes, the next request for that cell tries the provider again.
- **Why:** Without sharing, 20 requests at an expiry moment would send 20 provider calls, and during an outage 20 separate retry chains. That loads a provider that is already failing, and each waiting request would pay for its own retries. Sharing costs one call, and it makes the answer the same for everyone who asked at the same time. Trade-off: more code and some subtle cases (a caller leaving, a new request arriving just as a fetch ends). They are covered by tests. Not remembering failures means a long outage causes one retry chain per request that arrives after the previous one ends. A short back-off could reduce that, but it is not in the assignment and was left out.

## Every weather-service setting is required in `.env`, except the API key, and is checked at startup

- **Question:** P2 says every value that can change between environments lives in `.env`, and a service must start with a clear error when a required variable is missing. Which settings have defaults in code, and how strictly are the values checked?
- **Suggested:** No defaults in code except for the API key, which may be empty. Check every value when the service starts. Labelled as personal judgment.
- **Decision:** `PROVIDER_BASE_URL`, `PROVIDER_TIMEOUT_SECONDS`, `PROVIDER_RETRIES`, `PROVIDER_RETRY_DELAY_SECONDS`, `FRESHNESS_HOURS`, `MAX_STALE_HOURS` and `RETRY_AFTER_SECONDS` have no default in code. `PROVIDER_API_KEY` may be empty, because the free plan needs no key. The service refuses to start, with a message naming the variable, if a value is missing or invalid:
  - the URL must start with `http://` or `https://`;
  - timeout must be above 0, retries and delay 0 or more, retry-after above 0;
  - freshness and the stale limit must be above 0, at most 8760 hours (one year), and the stale limit must not be below freshness;
  - `nan` and `inf` are refused for every number.

  Other variables in `.env` (for example a later service's) are ignored. `.env.example` lists every variable with a safe example value.
- **Why:** A default in code hides a choice nobody made, and it could silently differ in production. With none, `.env.example` is the complete list of what the person setting up the service has to decide. `nan` passes "greater than 0" checks (every comparison with `nan` is false), and a huge number of hours would overflow date calculations, so both would start the service and then break every request. Failing at startup finds that at once. Trade-off: slightly more setup for a new developer, who copies `.env.example` to `.env`. The registry follows the same pattern with `DATABASE_URL`.

## The planner uses the single crop coefficient (FAO-56 Chapter 6), not the dual one

- **Question:** FAO-56 recommends the dual coefficient (Kcb + Ke) for drip irrigation, but it needs wind, humidity and soil-evaporation inputs that `weather-service` does not give. Which method does the planner use?
- **Suggested:** The single coefficient: ETc = Kc × ET0, with Kc following the FAO-56 curve for the growth stage. Labelled as personal judgment.
- **Decision:** The planner uses the single crop coefficient from Chapter 6, with Kc values and stage lengths for tomato and bell pepper. Chapter 7 (the dual method, soil-evaporation layer) is out of scope. The README and the `irrigation-calc-reference` skill state that this is an approximation, and that FAO-56 names the dual method as better suited to drip.
- **Why:** `weather-service` provides only ET0 and rain, the assignment describes Kc as a factor on ET0, and FAO-56 accepts the single coefficient for results of this kind. Trade-off: the later stages have no drip-specific correction, so the plan can be less accurate for drip than a dual-method plan.

## On an irrigation day the planner refills the accumulated depletion

- **Question:** The course's worked example shows `litres` equal to one day's crop use (6.9 mm × 1000 m² = 6900 L). The assignment also says to irrigate when the bucket "would fall below half". On a day when the threshold is crossed, how much water does the plan apply?
- **Suggested:** Refill the bucket to full before that day's crop use, which can be several days of use. Labelled as personal judgment.
- **Decision:** `litres` is the accumulated depletion (after the day's rain) times the plot area, and never more, so nothing is wasted. The crop's use that day then draws the bucket down again. The depth is not returned; only `litres` and `run_minutes` are. The instructor said to apply our judgment.
- **Why:** Applying only the day's use would leave the bucket draining after each irrigation, so it would cross the threshold again the next day. Refilling matches FAO-56's rule that the net irrigation depth is at most the depletion (Chapter 8) and the assignment's bucket example, where day 6 irrigates 35 mm, not 7 mm. Trade-off: it does not reproduce the worked example's 6900 L on a day when the depletion is larger. It does reproduce the example's emitter arithmetic.

## An irrigation is decided on the level at the end of that day, and counts that morning

- **Question:** On which day does an irrigation happen: the morning after the level has already crossed the threshold (FAO-56 Annex 8), or the day it would cross?
- **Suggested:** The day it would cross. Labelled as personal judgment.
- **Decision:** For each day the planner takes the depletion after that morning's rain and adds the day's crop use. If that is above the allowed depletion (strictly above; exactly at it does not irrigate), the plan irrigates that morning for the depletion, and the day ends with only the day's crop use drawn. Rain is applied first, and all forecast rain counts.
- **Why:** It matches the assignment's example, where day 6 "would drop below half, so you irrigate", and it never lets the crop go below the threshold. Annex 8 irrigates the next morning and accepts a day of mild stress. Trade-off: irrigation comes one day earlier than in Annex 8, so a little more water is used.

## The planner's crop numbers live in a cited Python module

- **Question:** The planner needs numbers per crop (Kc values, stage lengths, root depth, depletion fraction). Where do they live?
- **Suggested:** A Python module, `crops.py`, with a cited FAO-56 source beside each number. Labelled as personal judgment.
- **Decision:** The crop table is a Python module of typed, immutable constants. Every number has a comment naming its FAO-56 table, and a value that is a choice rather than a printed number says so. Each value is one named constant, so changing it is a one-line edit. They are not environment variables and not a data file.
- **Why:** Crop coefficients are domain knowledge that does not change between environments, which is what `.env` is for. A Python module is type-checked, testable, and keeps the citation next to the number. Trade-off: a change means editing code and redeploying, which a data file would avoid. The alternatives were a JSON or YAML file (needs a loader and a validator, awkward for citations) and `.env` variables (over 20 of them, no room for sources).

## The planner uses plain floats and rounds only in the response

- **Question:** Should the engine's arithmetic use `Decimal` or floats, and where does rounding happen?
- **Suggested:** Floats, with rounding only when the response is built. Labelled as personal judgment.
- **Decision:** The engine works in full-precision floats and never rounds. The response rounds to 2 decimals for millimetres, litres and minutes, and to 3 for Kc. Rounded values are never fed back into the calculation.
- **Why:** The calculation is a short chain of multiplications, subtractions and comparisons, and float error is far below any meaningful tolerance. Rounding between days would accumulate error. The weather service needed exact decimals for cell edges, which is a different problem. Trade-off: a comparison exactly at the threshold depends on the float values, so the threshold tests use inputs that are exact in binary.

## An invalid or non-finite upstream answer makes the plan unavailable, never a guess

- **Question:** What does the planner do when the registry or the weather service answers `200` with data it cannot trust?
- **Suggested:** Treat it as that service being unavailable. Labelled as personal judgment.
- **Decision:** The planner validates every upstream answer strictly: types, finite numbers, positive where required, and for the forecast exactly the requested number of consecutive days with a boolean `stale`. Anything else is `503 UPSTREAM_UNAVAILABLE` naming the service, and the plan is never padded or defaulted. If the engine produces a non-finite number, the answer is also `503`, with a detail naming both services because the culprit cannot be told.
- **Why:** A plan of zeros, or a number the engine did not produce, reads as "no water needed". An out-of-range value that produced `null` in the JSON was found in review and is now refused. Trade-off: one bad value among many throws away the whole plan.

## The crop values are our judgment calls, taken from FAO-56 and changeable later

- **Question:** Which values does the planner use for each crop, given that FAO-56 gives ranges and the assignment says to irrigate when the bucket "would fall below half"?
- **Suggested:** The FAO-56 values, with the lower end of the root depth. Labelled as personal judgment.
- **Decision:** Tomato: Kc 0.6 / 1.15 / 0.80, stages 30 / 40 / 45 / 30 days, root depth 0.7 m, depletion fraction `p` 0.40. Bell pepper: Kc 0.6 / 1.05 / 0.90, stages 30 / 35 / 40 / 20 days, root depth 0.5 m, `p` 0.30. `p` comes from FAO-56 Table 22, not from the assignment's "half". The climate adjustment of Kc, FAO's ETc adjustment of `p` and the wetted-fraction adjustment are not applied. The instructor said to apply our judgment and that values can be changed later.
- **Why:** The assignment's "half" is an explanation in "The ideas you need", and FR-2.11 says numbers follow the project skill, which follows FAO-56. The lower root depth is the one FAO-56 recommends for scheduling. Trade-off: the stage lengths are indicative and FAO-56 itself says to use local data, and tomato's `Kc_end` is the middle of a printed range of 0.70 to 0.90.

## An unexpected internal error returns 503 UNAVAILABLE as problem+json, in all three services

- **Question:** The spec says every error response is `application/problem+json`, but an unhandled exception gives a plain-text `500 Internal Server Error`. Which `code` does such an error carry?
- **Suggested:** `503 UNAVAILABLE`, with no new code. Labelled as personal judgment.
- **Decision:** Each service registers a catch-all handler. Any unhandled exception returns `503`, `application/problem+json`, `code` `UNAVAILABLE`, and a generic `detail` ("The service hit an unexpected error"). There is no `Retry-After`, because the cause is not known to be temporary. The exception is logged with its traceback. Nothing from it (messages, values, URLs) goes into the response. The existing specific answers (`404`, `409`, `422`, and the `503` with `Retry-After` for a database connection failure or pool timeout) are unchanged. For unexpected errors this overrides the P1 entry "A database connection failure returns 503", which says other database errors are not converted: they now return `503`, not a plain `500`.
- **Why:** The spec says every error uses `problem+json`, and the five existing codes already have one that fits "this service can't answer right now". Clients and the frontend already handle `503 UNAVAILABLE`. Trade-off: a real bug looks like a temporary outage to a client, and `503` invites retries. The log holds the truth. A `500` would be more accurate but needs a sixth code in the spec.

## The frontend's headline shows whole minutes, rounded up

- **Question:** The planner returns `run_minutes` with decimals, for example 341.55. How does the plot page's headline ("Water for N minutes") show it?
- **Suggested:** Whole minutes. First suggested rounding to the nearest minute, never below 1. Labelled as personal judgment.
- **Decision:** The headline shows whole minutes, rounded up. A run above 0 is never shown as 0, and the crop never gets less than the planned time. This is display formatting only: the planner's numbers are not changed, and the plan list shows `litres` as the planner gave them. The learner chose rounding up.
- **Why:** A grower sets a timer in whole minutes, and rounding up keeps "Water for 1 minute" for a run of 0.3. Trade-off: the headline can be up to one minute longer than the planned run, which is under 1% of a typical run. `CLAUDE.md` rule 12 says no model adjusts irrigation numbers; this is a display rule, and it is logged so it stays visible.

## The frontend's headline says "about" when the minutes were rounded up

- **Question:** The headline shows whole minutes rounded up ("Water for 342 minutes"), but the plan list shows the planner's exact minutes for the same day ("341.55 minutes"). A grower sees two numbers for one day. How do the two agree?
- **Suggested:** Either round the list too, or label the headline. Labelled as personal judgment.
- **Decision:** The headline says "about" when rounding changed the number ("Water for about 342 minutes"). A whole number of minutes from the planner has no "about". The plan list still shows the planner's exact minutes. The learner chose this. It adds to the entry "The frontend's headline shows whole minutes, rounded up", which stays as written.
- **Why:** "About" makes the headline agree with the list instead of contradicting it, and the list stays the planner's numbers as given. Trade-off: "about" is vaguer than a number, but it never contradicts the list.
