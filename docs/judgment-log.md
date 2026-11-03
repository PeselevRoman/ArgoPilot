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
