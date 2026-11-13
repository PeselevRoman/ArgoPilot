# Judgment log

## Unknown farm on plot create returns 422

- **Question:** What should `POST /v1/plots` return when `farm_id` names a farm that doesn't exist: `422 VALIDATION` or `404 NOT_FOUND`?
- **Suggested:** `422 VALIDATION`, for three reasons:
  - Consistency: all four body references (`farm_id`, `crop_id`, `soil_id`, `emitter_id`) behave the same way, so a client learns one rule.
  - Where the problem is: `POST /v1/plots` is a valid URL, and the body contains an invalid reference. That is the 422 case.
  - Clear client signal: the `detail` field can say "Unknown farm", so the client knows which field to fix.
- **Decision:** `422 VALIDATION`.
- **Why:** The problem is in the body of the request, not in the URL. `404` is reserved for a missing resource in the URL path, such as `GET /v1/farms/{id}`.

## Unknown farm on plot list returns an empty list

- **Question:** What should `GET /v1/plots?farm_id=…` return when no farm has that id: `404` or `200 []`?
- **Suggested:** `200 []`, for two reasons:
  - The spec already states the rule for lists, so this only adds an exception to it.
  - The typo risk is real, but the client can check the farm with `GET /v1/farms/{id}` if it needs to tell the two cases apart.
- **Decision:** `200 []`.
- **Why:** `404` is reserved for wrong requests, not for sub-queries. A filter that matches nothing is an empty result, the same as a farm with no plots.

## Extra fields in a request body are ignored

- **Question:** Should request bodies with fields outside the spec be rejected or ignored?
- **Suggested:** No recommendation. 
- **Decision:** Ignored.
- **Why:** Ignoring unknown fields lets newer clients send fields that this version doesn't know yet, without getting an error. Trade-off: a typo in an optional field name is dropped silently. Rejecting unknown fields would catch those typos, but breaks newer clients.

## Wrong method on any route returns 405 with code VALIDATION

- **Question:** FastAPI's default 405 response is JSON with no `code`, which breaks the rule that every error has one of four codes. Which code should the 405 use?
- **Suggested:** Three options: add a fifth code (`METHOD_NOT_ALLOWED`), use `VALIDATION`, or return `405` with no code. Leaned toward `VALIDATION`, labelled as personal judgment.
- **Decision:** Return `405` as `application/problem+json` with `code: VALIDATION` for any route that doesn't allow the method, and keep the `Allow` header.
- **Why:** The spec lists only four codes, and FR-1.4 requires one of them. `VALIDATION` is the closest match, since the request is wrong for that route. A fifth code would go against the spec's list.

## Database outage is tested by overriding the database dependency

- **Question:** How should the `503 UNAVAILABLE` case be tested without a real outage?
- **Suggested:** Override the database dependency in the test. Pointing the app at an unreachable path was the alternative, and was marked as fragile. Labelled as industry consensus.
- **Decision:** Override the database dependency in the test so it raises an error.
- **Why:** The test doesn't depend on file permissions, paths, or the machine, so it behaves the same everywhere. The alternative, pointing the app at an unreachable path, is fragile.

## Database is checked before connecting

- **Question:** SQLite creates a missing file on connect, so how is "database unreachable" detected?
- **Suggested:** Check that `registry.db` exists before connecting, and return `503` if it doesn't.
- **Decision:** Check that `registry.db` exists before connecting. If it doesn't, return `503 UNAVAILABLE`.
- **Why:** Without the check, SQLite would create an empty database, and every request would then fail with a `500` error, because the tables don't exist. The check makes a missing database return `503` instead.

## Status title uses the standard reason phrase

- **Question:** The spec's example title for `422` says "Unprocessable Entity", but the standard library says "Unprocessable Content". Which should the service use?
- **Suggested:** Use the standard phrase from the library. Offered matching the spec example as the alternative.
- **Decision:** The standard reason phrase from the library.
- **Why:** The spec example is illustrative, not a requirement. Using the standard phrase keeps titles consistent with the status codes.

## Status 400 maps to VALIDATION

- **Question:** The spec lists no code for `400`. Which code should it use?
- **Suggested:** `VALIDATION`, since it means the request is invalid. Offered for confirmation with a test case.
- **Decision:** `VALIDATION`.
- **Why:** A `400` means the request is invalid, which is what `VALIDATION` describes. This keeps the spec's four codes. No route returns `400` yet; the mapping is ready for when one does.

## Catalogues are read from the database

- **Question:** Should the crop, soil, and emitter data come from the database or from constants in code?
- **Suggested:** From the database, since it's the single source of truth. Labelled as personal judgment.
- **Decision:** From the database, seeded by `seed_registry.sh`.
- **Why:** The database is the single source of truth in this design. The spec's seed defines the catalogue values, and the database holds them.

## Tests use a temporary seeded database

- **Question:** How do the catalogue tests get data without touching `registry.db`?
- **Suggested:** Seed a temporary database for each test run and point the app at it.
- **Decision:** Each test run seeds a temporary database and points the app at it.
- **Why:** Tests stay isolated from your real data. They need `bash` and `sqlite3` installed, so they run the same on any machine that has them.

## Tests use a dedicated catalogue-only database script

- **Question:** Which data should the tests use, and where does it come from?
- **Suggested:** A separate script in `tests/` that seeds only the catalogue tables with the spec's values, so tests don't depend on `registry.db` or the tasks copy. Labelled as personal judgment.
- **Decision:** The tests run `tests/seed_test_db.sh` into a temporary folder for each test. It seeds the catalogue tables only.
- **Why:** The catalogue tests need only catalogue data. Keeping test data separate from `registry.db` keeps tests isolated. Farms and plots are added when their steps need them.

## Lists are sorted by id

- **Question:** The spec doesn't say how list results are ordered. How should they be ordered?
- **Suggested:** Sort by `id`, so the output is deterministic. Labelled as personal judgment.
- **Decision:** All list endpoints sort by `id`.
- **Why:** SQLite doesn't guarantee row order without a sort, and stable output keeps the tests and API clients predictable.

## The course seed script keeps its own table definitions

- **Question:** Should `tasks/seed_registry.sh` load the shared `schema.sql`, so both seed scripts use one schema?
- **Suggested:** Load the shared file in both scripts, so the table definitions live in one place. Labelled as industry consensus.
- **Decision:** `tasks/seed_registry.sh` stays unchanged, with its own table definitions. `schema.sql` is used only by `tests/seed_test_db.sh`.
- **Why:** The course script is provided by the course, so it should not be changed. Trade-off: the two copies of the table definitions can drift apart again.
- **Updated:** `schema.sql` is also used by `tests/test_schema.py`, which checks it against a saved copy of the course tables. See "The schema check uses a saved copy of the course tables".

## Tests fail when the course schema and schema.sql differ

- **Question:** The course seed script and `schema.sql` define the same tables twice. How do we know when they drift apart?
- **Suggested:** A test that builds a database from each and compares their structure. Labelled as personal judgment.
- **Decision:** The test fails and names the table that differs.
- **Why:** The two copies can drift apart without any other test failing. Comparing their structure catches that, and a failing test is harder to miss than a warning.
- **Updated:** Replaced by "The schema check uses a saved copy of the course tables". The test no longer reads the course script. It compares `schema.sql` with a saved copy in `tests/`. It still fails and names the table that differs.

## The schema check uses a saved copy of the course tables

- **Question:** How can the schema check run without reading the course seed script?
- **Suggested:** Save the expected table structure in `tests/` and compare `schema.sql` against it. Labelled as personal judgment.
- **Decision:** The test compares `schema.sql` with a saved copy in `tests/`. It no longer reads `tasks/seed_registry.sh`.
- **Why:** The test no longer depends on course files, so the course file can be removed later without breaking tests. Trade-off: the saved copy is a second copy of the structure, and it must be updated on purpose when the schema changes.

## Farm ids are generated by the server with uuid4

- **Question:** Who creates a farm's id, the client or the server?
- **Suggested:** The server creates a random UUID (`uuid4`). Labelled as industry consensus.
- **Decision:** The server generates the id with `uuid4`.
- **Why:** This is the usual default, and `uuid4` works on every Python version the project supports.

## Names are trimmed, and blank names are rejected

- **Question:** What should happen to a name made of spaces, or with spaces at the ends?
- **Suggested:** Reject a blank name with `422 VALIDATION`, and store the name as sent. Labelled as industry consensus.
- **Decision:** Leading and trailing spaces are removed. A name that is blank after trimming returns `422 VALIDATION`.
- **Why:** Leading and trailing spaces are usually a mistake, and a blank name is effectively empty, which the spec does not allow.

## PATCH cannot set a farm's name to null

- **Question:** What should `PATCH` do with `"name": null`?
- **Suggested:** Reject it with `422 VALIDATION`. Labelled as industry consensus.
- **Decision:** An omitted name leaves the farm unchanged. A null name returns `422 VALIDATION`.
- **Why:** A farm must have a name, so null is never a valid change.

## Deleting a farm with plots returns 409 CONFLICT

- **Question:** What should happen when a farm still has plots?
- **Suggested:** Check for plots in the route, and also convert the database's refusal into `409`, in case a plot is added between the check and the delete. Labelled as industry consensus.
- **Decision:** Delete returns `409 CONFLICT` when the farm has plots, whether the check or the database finds them.
- **Why:** The check gives a clear answer. The database error covers the rare case of a plot added in between. Without it, that request would fail with an unformatted `500`.
- **Updated:** The same handling covers plots. If a farm is deleted while a plot is being created or moved onto it, the request returns `422 Unknown farm` instead of a `500`.

## Each request is one transaction

- **Question:** When should a route's writes be saved?
- **Suggested:** Commit after each write, or use one transaction per request. The second is the common pattern in larger services. Labelled as industry consensus.
- **Decision:** Each request is one transaction. Its changes are saved only if the route finishes without error, and the commit happens before the response is sent.
- **Why:** Routes with several writes stay safe later, and no route has to remember to commit. Committing before the response means a client that reads right after a write sees the change.

## Retry-After is 5 seconds for now

- **Question:** How long should a client wait before retrying after a `503`?
- **Suggested:** 5 seconds as a placeholder. Labelled as personal judgment.
- **Decision:** 5 seconds, subject to change once a real outage shows what fits.
- **Why:** The spec gives no number, and a local SQLite file has no outage pattern yet to base a number on.

## The database path is resolved from the code's location

- **Question:** Should `registry.db` be found relative to the working folder, or relative to the code?
- **Suggested:** Resolve it from the folder that holds `db.py`, using `Path(__file__).parent`. Labelled as personal judgment.
- **Decision:** The path is resolved from the folder that holds `db.py`.
- **Why:** The server works from any working directory. A relative path would break as soon as the server started from another folder.
- **Updated:** A relative SQLite path in `DATABASE_URL`, such as `sqlite:///registry.db`, is resolved from the same folder, and the `.env` file is read from it.

## A string that holds a number is converted to a number

- **Question:** Should a number sent as text, such as `"1000"`, be accepted?
- **Suggested:** Reject it, using strict types, as the safer default. Labelled as personal judgment.
- **Decision:** A string that holds a number is converted to a number. Non-numeric strings, booleans, and infinity are rejected.
- **Why:** Clients often send numbers as text, and converting them is more forgiving. Booleans are refused because Python would count them as 1 or 0. Infinity is refused because no plot can have an infinite area or coordinate.
- **Updated:** Underscores are rejected (`"1_000"`), since Python reads them as separators but clients should not send them. Commas are accepted only as thousands separators in groups of three (`"1,000"`, `"1,234,567.5"`). Other comma forms, such as `"1,5"`, are rejected.

## A PATCH must leave the plot valid

- **Question:** What happens when a PATCH would leave a plot invalid?
- **Suggested:** Check the whole plot after the change, and reject the request if any rule fails. Labelled as personal judgment.
- **Decision:** The changed plot must pass every rule before anything is saved. Otherwise the request returns an error and nothing changes.
- **Why:** A PATCH must not leave a plot half-valid. Checking only the new values could miss a rule that depends on the rest of the plot. For example, moving a plot to another farm can create a duplicate name there, and checking the farm id alone would not catch it.

## A planting date may not be in the future

- **Question:** What counts as "in the future" for `planting_date`?
- **Suggested:** Compare dates only, against the server's date. Labelled as personal judgment.
- **Decision:** `planting_date` may be today or earlier. A later date returns `422`. The comparison uses the server's local date.
- **Why:** The spec gives no timezone, and comparing dates only avoids problems with the time of day. Trade-off: a client in another timezone can see a different "today".

## A plot name is unique within its farm

- **Question:** How far does the plot name rule reach?
- **Suggested:** Unique inside one farm, as the spec says. The same name on another farm is allowed. Labelled as industry consensus.
- **Decision:** A plot name must be unique within its farm. The same name on another farm is allowed.
- **Why:** The spec defines the rule this way. A duplicate returns `409 CONFLICT`, whether the route's check or the database finds it.

## Plot names follow the farm name rule

- **Question:** How are plot names trimmed and checked for blanks?
- **Suggested:** Use the same rule as farm names. Labelled as personal judgment.
- **Decision:** Leading and trailing spaces are removed. A name that is blank after trimming returns `422`.
- **Why:** Names follow one rule across the API. Leading and trailing spaces are usually a mistake, and a blank name is invalid.

## The load test uses k6 at a fixed rate

- **Question:** Which load test tool measures NFR-1.1, and how does it send requests?
- **Suggested:** k6, with a fixed arrival rate. Labelled as industry consensus.
- **Decision:** k6 sends 10 requests per second, with a p95 threshold of 100 ms for each endpoint.
- **Why:** A fixed rate avoids hiding slow responses. k6 reports percentiles and fails the run when the threshold is missed. Trade-off: k6 is a system tool, installed outside `uv`.

## The performance database has 100 farms and 10,000 plots

- **Question:** How much data should the performance check use?
- **Suggested:** 100 farms and 10,000 plots, spread across the farms, so list routes return a realistic amount. Labelled as personal judgment.
- **Decision:** The performance check uses 100 farms and 10,000 plots, generated by a script in a separate database from `registry.db`.
- **Why:** The spec gives no size. Lists need enough rows to be meaningful, and a separate database keeps `registry.db` unchanged.

## The service keeps its own copy of the seed script

- **Question:** The seed script is course material in `tasks/`, which won't ship with the product. How does the README create the database?
- **Suggested:** Copy the script into the service folder, and leave the course file unchanged. Labelled as personal judgment.
- **Decision:** `services/registry-service/seed_registry.sh` is a copy of the course script, and the README uses it.
- **Why:** The product must be runnable without course material, and keeping the course file unchanged respects the course.
- **Updated:** The service's seed script no longer holds its own table definitions. See "The service's seed script loads the shared schema".

## The service's seed script loads the shared schema

- **Question:** The service's seed script copies the table definitions, so there are two copies to keep in step. How should the seed get its tables?
- **Suggested:** Load `schema.sql` in the seed script, so the product has one table definition. The course file stays unchanged. Labelled as industry consensus.
- **Decision:** `services/registry-service/seed_registry.sh` loads `schema.sql` and inserts the sample data. It no longer holds its own table definitions.
- **Why:** A change to the table definitions is made in one place, and the seed and the tests both use it. The course file still stays unchanged.

---

# PostgreSQL support

Decisions about running the service on PostgreSQL in production. `DATABASE_URL` selects the engine: SQLite (`registry.db`) locally and in tests, PostgreSQL in production. The existing endpoints must behave exactly the same on both.

## Postgres uses native column types

- **Question:** The production PostgreSQL tables must match the local SQLite schema. Should they keep the SQLite types, or use Postgres's native types?
- **Suggested:** Keep the SQLite types (`text`, with `double precision` for `REAL`), so both engines share one code path and return the same values. Labelled as personal judgment.
- **Decision:** Native types: `uuid` for farm and plot ids (and `plots.farm_id`), `date` for `planting_date`, `double precision` for the floats. Catalogue ids stay `text`, since they are slugs, not UUIDs.
- **Why:** The database should reject bad dates and malformed ids itself, not rely only on the API's validation. Trade-off: the two engines return different Python types, so the code needs a conversion layer to keep the API output identical, and tests on SQLite say less about Postgres.

## SQLAlchemy Core talks to both databases

- **Question:** Every route uses `sqlite3` directly with `?` placeholders. How should the code work with both SQLite and PostgreSQL?
- **Suggested:** SQLAlchemy Core, so queries are written once and the engine comes from `DATABASE_URL`. Alternatives: raw SQL with a hand-written adapter per driver, or the full SQLAlchemy ORM. Labelled as industry consensus.
- **Decision:** SQLAlchemy Core.
- **Why:** It converts `UUID` and `date` values for each engine and keeps one version of each query, so the endpoints can behave the same on both. Trade-off: one new dependency, and the routes' SQL has to be rewritten.

## DATABASE_URL has no default

- **Question:** What should the app do when `DATABASE_URL` is not set?
- **Suggested:** Fail at startup with no default, so a production deploy that forgets the variable stops at once. The alternative was to default to `sqlite:///registry.db`, which makes local runs easier but could silently start production on a local file. Labelled as personal judgment.
- **Decision:** No default. The app refuses to start without `DATABASE_URL`. A committed `.env.example` shows the format, and the real `.env` stays out of git.
- **Why:** A missing production setting should stop the deploy, not fall back quietly. Trade-off: local runs need a `.env` file first.

## Tests run on SQLite, plus on PostgreSQL when one is available

- **Question:** The two engines return different Python types, so tests on SQLite alone don't prove the Postgres path works. How should tests treat PostgreSQL?
- **Suggested:** Run the API tests on SQLite by default, and also on a real Postgres when `TEST_DATABASE_URL` is set. Alternatives: SQLite only, or Postgres for every run. Labelled as industry consensus.
- **Decision:** SQLite by default. The Postgres tests run only when `TEST_DATABASE_URL` is set, and are skipped otherwise. No Docker or CI exists yet, so a local Postgres install (WSL) is the way to run them for now.
- **Why:** The real engine is the only way to check that behavior is identical on both, and skipping keeps the normal run fast and free of setup. Trade-off: until a Postgres is set up, the Postgres path is untested, and a skipped test can hide that.

## A database connection failure returns 503

- **Question:** Today "database unreachable" means the SQLite file is missing. How is it detected on PostgreSQL?
- **Suggested:** Keep the SQLite file check, and on Postgres catch the connection error and return the same `503`. A startup connection check was the alternative, but a short outage at startup would then stop the app from starting. Labelled as industry consensus.
- **Decision:** A failure to connect to the database returns `503 UNAVAILABLE` with `Retry-After: 5`, on both engines, and the underlying error is logged. Other database errors are not converted. The app does no connection check at startup.
- **Why:** A `503` with `Retry-After` is the signal for a temporary outage, and the response stays identical to today's. Trade-offs: (1) a wrong password or database name in `DATABASE_URL` never fixes itself, but clients get a `503` telling them to retry, so the log is the only place the cause shows. (2) If the tables were never created, the first request fails with an unformatted `500`, because the connection itself works.

## PostgreSQL gets its own schema file

- **Question:** The service never creates tables in production, but the Postgres tables must exist before release and for the Postgres tests. Where is their definition kept?
- **Suggested:** A second file, `schema.postgres.sql`, next to `schema.sql`, with a test that compares the two files' tables and columns. The alternative was to generate the DDL for both engines from SQLAlchemy table definitions. Labelled as personal judgment.
- **Decision:** `services/registry-service/schema.postgres.sql` holds the Postgres table definitions with the native types. It is run once before release and loaded by the Postgres tests. The service never runs it.
- **Why:** The native types make the two engines' definitions differ, and a plain SQL file is easy to read and review before running on production. Trade-off: the two files can drift apart, so a test must compare their tables and columns.

## Malformed ids behave as before; UUID text is accepted in any form

- **Question:** With `uuid` columns, a malformed id in a path, body or query would make the database raise an error. What should the API return?
- **Suggested:** Parse the id first. A malformed id behaves as an id that matches nothing, so responses stay as they are today. Labelled as personal judgment.
- **Decision:** A malformed path id returns `404`, a malformed body `farm_id` returns `422 Unknown farm`, and `?farm_id=` with a malformed value returns `200 []`. UUID text in uppercase or without hyphens is valid and finds the row.
- **Why:** The responses stay identical to today's for every malformed id. Trade-off: this is the one place behavior differs from before, because uppercase or hyphenless UUIDs used to return `404` and now find the row.

## Catalogue ids sort by byte order on PostgreSQL

- **Question:** Lists sort by `id`. SQLite sorts text by bytes, and Postgres by the database's locale rules. How do the lists stay in the same order?
- **Suggested:** Use byte-order collation (`COLLATE "C"`) on the catalogue `id` columns in `schema.postgres.sql`. Labelled as personal judgment.
- **Decision:** The catalogue `id` columns use `COLLATE "C"` in the Postgres schema.
- **Why:** Today's ids sort the same either way, but a future id with punctuation could sort differently. Trade-off: one more detail in the Postgres schema to keep in mind.

## A failed write rolls back before the re-check

- **Question:** On PostgreSQL a failed statement aborts the whole transaction, so the re-check queries that follow an `IntegrityError` would fail with a `500`. How do the `409` and `422` answers survive?
- **Suggested:** Roll back the transaction, then run the re-check. The alternative was a savepoint around the write, which keeps earlier work in the request but has known trouble with SQLite's driver. Labelled as personal judgment.
- **Decision:** In `create_plot`, `update_plot` and `delete_farm`, the `IntegrityError` handler calls `conn.rollback()` before the re-check.
- **Why:** The failing write is the only write in each of those requests, so the rollback loses nothing, and it behaves the same on both engines. Trade-off: a future route that writes several things before the one that fails would lose that work, and would need a savepoint instead.

## Ids use a custom column type, not SQLAlchemy's Uuid

- **Question:** SQLAlchemy's built-in `Uuid` stores ids on SQLite as 32 hex characters without hyphens. The existing `registry.db` rows have hyphenated ids. Which column type should the id columns use?
- **Suggested:** A small custom type that stores hyphenated text on SQLite and uses the native `uuid` on Postgres. Alternatives: migrate the SQLite data to the hex form, or keep ids as plain strings. Labelled as personal judgment.
- **Decision:** `UuidId` in `tables.py`: a hyphenated lowercase text column on SQLite, a native `uuid` on Postgres, and a Python `UUID` in both.
- **Why:** Existing databases and `schema.sql` keep working with no data change, and both engines give the code the same Python type. Trade-off: one custom type to maintain.

## Connection tests use an unreachable Postgres port

- **Question:** How is the `503` for an unreachable Postgres tested, when the override method used for the older `503` test cannot check the Postgres connection path?
- **Suggested:** Point the new connection dependency at a closed port, `postgresql://u:p@127.0.0.1:1/test`. Labelled as personal judgment.
- **Decision:** The new dependency's `503` test uses a real unreachable Postgres URL. The override decision above still covers the route-level test.
- **Why:** Only a real connection attempt exercises the Postgres connection error that the `503` depends on. Trade-off: the test depends on nothing listening on local port 1, and it is slower than an override.

## Pool timeouts return 503

- **Question:** What should a request return when the database connection pool has no free connection within its wait time?
- **Suggested:** The same `503 UNAVAILABLE` with `Retry-After: 5` as a failed connection, since both mean the database is temporarily unavailable. Labelled as personal judgment.
- **Decision:** A connection-pool timeout returns `503 UNAVAILABLE` with `Retry-After: 5`, the same as a failed connection.
- **Why:** The client sees one signal for a temporarily unavailable database instead of an unformatted `500`. Trade-off: a saturated pool is reported as an outage, which can hide a slow query.
