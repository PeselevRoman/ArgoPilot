# Judgment log

## Unknown farm on plot create returns 422

- **Question:** What should `POST /v1/plots` return when `farm_id` names a farm that doesn't exist: `422 VALIDATION` or `404 NOT_FOUND`?
- **Suggested:** Claude on the web recommended `422 VALIDATION`, for three reasons:
  - Consistency: all four body references (`farm_id`, `crop_id`, `soil_id`, `emitter_id`) behave the same way, so a client learns one rule.
  - Where the problem is: `POST /v1/plots` is a valid URL, and the body contains an invalid reference. That is the 422 case.
  - Clear client signal: the `detail` field can say "Unknown farm", so the client knows which field to fix.
- **Decision:** `422 VALIDATION`.
- **Why:** The problem is in the body of the request, not in the URL. `404` is reserved for a missing resource in the URL path, such as `GET /v1/farms/{id}`.

## Unknown farm on plot list returns an empty list

- **Question:** What should `GET /v1/plots?farm_id=…` return when no farm has that id: `404` or `200 []`?
- **Suggested:** Claude on the web recommended `200 []`, for two reasons:
  - The spec already states the rule for lists, so this only adds an exception to it.
  - The typo risk is real, but the client can check the farm with `GET /v1/farms/{id}` if it needs to tell the two cases apart.
- **Decision:** `200 []`.
- **Why:** `404` is reserved for wrong requests, not for sub-queries. A filter that matches nothing is an empty result, the same as a farm with no plots.

## Extra fields in a request body are ignored

- **Question:** Should request bodies with fields outside the spec be rejected or ignored?
- **Suggested:** No recommendation. The options were offered for the learner to choose.
- **Decision:** Ignored.
- **Why:** Ignoring unknown fields lets newer clients send fields that this version doesn't know yet, without getting an error. Trade-off: a typo in an optional field name is dropped silently. Rejecting unknown fields would catch those typos, but breaks newer clients.

## Wrong method on catalogue routes returns 405 with code VALIDATION

- **Question:** FastAPI's default 405 response is JSON with no `code`, which breaks the rule that every error has one of four codes. Which code should the 405 use?
- **Suggested:** Three options: add a fifth code (`METHOD_NOT_ALLOWED`), use `VALIDATION`, or return `405` with no code. Leaned toward `VALIDATION`, labelled as personal judgment.
- **Decision:** Return `405` as `application/problem+json` with `code: VALIDATION`, and keep the `Allow` header.
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
- **Why:** Without the check, a missing database would be silently created empty, so the `503` would never happen in real use.

## Status title uses the standard reason phrase

- **Question:** The spec's example title for `422` says "Unprocessable Entity", but the standard library says "Unprocessable Content". Which should the service use?
- **Suggested:** Use the standard phrase from the library. Offered matching the spec example as the alternative.
- **Decision:** The standard reason phrase from the library.
- **Why:** The spec example is illustrative, not a requirement. Using the standard phrase keeps titles consistent with the status codes.

## Status 400 maps to VALIDATION

- **Question:** The spec lists no code for `400`. Which code should it use?
- **Suggested:** `VALIDATION`, since it means the request is invalid. Offered for confirmation with a test case.
- **Decision:** `VALIDATION`.
- **Why:** A `400` means the request is invalid, which is what `VALIDATION` describes. This keeps the spec's four codes.

## Catalogues are read from the database

- **Question:** Should the crop, soil, and emitter data come from the database or from constants in code?
- **Suggested:** From the database, since it's the single source of truth. Labelled as personal judgment.
- **Decision:** From the database, seeded by `seed_registry.sh`.
- **Why:** The database is the single source of truth, and the spec treats the seed as the data.

## Tests use a temporary seeded database

- **Question:** How do the catalogue tests get data without touching `registry.db`?
- **Suggested:** Seed a temporary database for each test run and point the app at it.
- **Decision:** Each test run seeds a temporary database and points the app at it.
- **Why:** Tests stay isolated from your real data and run the same on every machine.

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
- **Why:** A PATCH must not leave a plot half-valid. Checking only the new values could miss a rule that depends on the rest of the plot, such as a farm that no longer exists.

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
