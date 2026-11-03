# Judgment log

## Unknown farm on plot create returns 422

- **Question:** What should `POST /v1/plots` return when `farm_id` names a farm that doesn't exist: `422 VALIDATION` or `404 NOT_FOUND`?
- **Decision:** `422 VALIDATION`.
- **Why:** The problem is in the body of the request, not in the URL. `404` is reserved for a missing resource in the URL path, such as `GET /v1/farms/{id}`.

## Unknown farm on plot list returns an empty list

- **Question:** What should `GET /v1/plots?farm_id=…` return when no farm has that id: `404` or `200 []`?
- **Decision:** `200 []`.
- **Why:** `404` is reserved for wrong requests, not for sub-queries. A filter that matches nothing is an empty result, the same as a farm with no plots.

## Extra fields in a request body are ignored

- **Question:** Should request bodies with fields outside the spec be rejected or ignored?
- **Decision:** Ignored.
- **Why:** Ignoring extra fields is good practice, and it keeps the API backward compatible: clients can send new fields without breaking the service.

## Wrong method on catalogue routes returns 405 with code VALIDATION

- **Question:** FastAPI's default 405 response is JSON with no `code`, which breaks the rule that every error has one of four codes. Which code should the 405 use?
- **Decision:** Return `405` as `application/problem+json` with `code: VALIDATION`, and keep the `Allow` header.
- **Why:** The spec lists only four codes, and FR-1.4 requires one of them. `VALIDATION` is the closest match, since the request is wrong for that route. A fifth code would go against the spec's list.

## Database outage is tested by overriding the database dependency

- **Question:** How should the `503 UNAVAILABLE` case be tested without a real outage?
- **Decision:** Override the database dependency in the test so it raises an error.
- **Why:** The test doesn't depend on file permissions, paths, or the machine, so it behaves the same everywhere. The alternative, pointing the app at an unreachable path, is fragile.

## Database is checked before connecting

- **Question:** SQLite creates a missing file on connect, so how is "database unreachable" detected?
- **Decision:** Check that `registry.db` exists before connecting. If it doesn't, return `503 UNAVAILABLE`.
- **Why:** Without the check, a missing database would be silently created empty, so the `503` would never happen in real use.

## Status title uses the standard reason phrase

- **Question:** The spec's example title for `422` says "Unprocessable Entity", but the standard library says "Unprocessable Content". Which should the service use?
- **Decision:** The standard reason phrase from the library.
- **Why:** The spec example is illustrative, not a requirement. Using the standard phrase keeps titles consistent with the status codes.

## Status 400 maps to VALIDATION

- **Question:** The spec lists no code for `400`. Which code should it use?
- **Decision:** `VALIDATION`.
- **Why:** A `400` means the request is invalid, which is what `VALIDATION` describes. This keeps the spec's four codes.
