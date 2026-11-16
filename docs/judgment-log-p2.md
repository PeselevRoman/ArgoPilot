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
