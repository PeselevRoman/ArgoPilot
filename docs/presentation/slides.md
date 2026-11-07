# Registry API: presentation content

Target: 15 minutes, 15 slides. Audience: the instructor, who will ask about my decisions.

---

## Slide 1: Registry API for AgroPilot
- Assignment P1: farms, plots, and read-only catalogues
- Built with FastAPI, SQLite, pytest, and uv
- Built step by step, with tests and small commits

Speaker notes: Introduce the project and what the assignment asked for. Say that the focus is the reasoning behind my choices, not a list of routes. Mention that I'll show the decisions, the tests, and the performance check.

Source: `tasks/p1_registry_api.md`, `CLAUDE.md`

---

## Slide 2: What the assignment asked for
- Farms and plots: create, read, update, delete
- Read-only crops, soils, and emitters
- Every error in one format with four codes
- p95 under 100 ms for GET list and GET by id

Speaker notes: Walk through the four requirements. Point out that every error must use `application/problem+json` with one of four codes. Say that the performance target applies only to GET routes, so POST and PATCH were left out of that check on purpose.

Source: `tasks/p1_registry_api.md` (FR-1.1 to FR-1.4, NFR-1.1)

---

## Slide 3: How I worked
- One step at a time: restate the step, confirm, then build
- Tests with every change
- Each decision confirmed and logged before it was used
- Small commits: 11 commits on `main` so far

Speaker notes: Explain the working rules from `CLAUDE.md`. The assistant suggested, and I confirmed. Decisions went into the judgment log only after I agreed to them. Each step was committed once its tests passed.

Source: `CLAUDE.md` (working rules 1, 4, 8, 9); `git log`

---

## Slide 4: Stack choices
- FastAPI: request validation and error handling built in
- SQLite: one file, no server to run
- pytest: test runner
- uv: dependency management with a lock file

Speaker notes: Keep this short. The stack was fixed before the work began. Explain that SQLite fits a single-user registry with one file, and that FastAPI's validation through Pydantic does much of the input checking.

Source: `CLAUDE.md` ("Stack (decided)"), `services/registry-service/pyproject.toml`

---

## Slide 5: Decision: unknown farm on create returns 422
- Choice: `422 VALIDATION`
- Alternative: `404 NOT_FOUND`
- Reason: the problem is in the request body, not the URL

Speaker notes: `404` is for a missing resource in the URL. The farm id is part of the body, so it's a validation problem. This matches how unknown crop, soil, and emitter ids are handled. The web suggestion for this choice was the same.

Source: `docs/judgment-log.md` ("Unknown farm on plot create returns 422")

---

## Slide 6: Decision: unknown farm in the plot list returns an empty list
- Choice: `200 []`
- Alternative: `404 NOT_FOUND`
- Reason: `404` is for wrong requests, not for sub-queries
- Trade-off: a typo in `farm_id` looks like a farm with no plots

Speaker notes: This is the one I'm least sure of. The spec already returns an empty list for an empty collection, so this is an exception to a rule the spec has. A client that needs to tell the two cases apart can call `GET /v1/farms/{id}`. I'd like your view on this one.

Source: `docs/judgment-log.md` ("Unknown farm on plot list returns an empty list")

---

## Slide 7: Decision: wrong method and status titles
- Wrong method on catalogues: `405` with code `VALIDATION`, and the `Allow` header kept
- Alternative: add a fifth code, which the spec doesn't list
- Status `400` maps to `VALIDATION`
- Title uses the standard phrase, not the spec example

Speaker notes: FastAPI's default `405` isn't problem+json and has no code, so a handler had to change it. The spec lists only four codes, so `VALIDATION` was the closest fit. The title was a small choice: the spec example says "Unprocessable Entity", but the standard phrase is "Unprocessable Content".

Source: `docs/judgment-log.md` (405, 400, and status title entries)

---

## Slide 8: Decision: how a database outage is detected and tested
- Choice: check that the file exists before connecting, and return `503`
- Testing: override the database dependency so it fails
- Alternative: point the app at an unreachable path, which is fragile

Speaker notes: SQLite creates a missing file on connect, so without the check a missing database would be silently created empty. The override test doesn't depend on file permissions or paths, so it runs the same everywhere.

Source: `docs/judgment-log.md` ("Database is checked before connecting", "Database outage is tested by overriding the database dependency")

---

## Slide 9: Decision: one transaction per request
- Choice: each request commits only if the route succeeds, before the response is sent
- Alternative: commit explicitly in each route
- Reason: routes that write several rows stay safe later
- Detail: the timing needed `scope="function"`, which needs FastAPI 0.162 or newer

Speaker notes: The first version committed inside each route. I switched to one transaction per request because a route that writes twice could save half its work. A test checks that a failed request leaves nothing behind. The FastAPI version was raised to match.

Source: `docs/judgment-log.md` ("Each request is one transaction"); `services/registry-service/db.py`; `services/registry-service/pyproject.toml`

---

## Slide 10: Decision: input rules for names and numbers
- Names: trimmed, then blank names rejected (my choice: trim; the assistant suggested storing names as sent)
- Numbers: text such as `"1000"` is converted
- Refused: booleans, infinity, underscores (`1_000`), and commas outside groups of three

Speaker notes: The assistant suggested storing names as sent, and I chose to trim them, because stray spaces are usually a mistake. For numbers, the assistant suggested strict types, and I chose conversion because clients often send numbers as text. I then refused the cases Python would quietly accept: `True` counts as 1, and `"1_000"` reads as 1000.

Source: `docs/judgment-log.md` ("Names are trimmed", "A string that holds a number is converted"); `services/registry-service/plots.py`

---

## Slide 11: Decision: plots must stay valid
- Choice: a `PATCH` checks the whole plot after the change, and saves nothing if it fails
- Alternative: check only the fields that were sent
- Name rule: unique within one farm, so the same name is allowed on another farm

Speaker notes: Checking only the new values could miss a rule that depends on the rest of the plot, such as a farm that was deleted. The duplicate-name rule is per farm, as the spec says. If a farm is deleted during a write, the route returns `422` instead of a `500`.

Source: `docs/judgment-log.md` ("A PATCH must leave the plot valid", "A plot name is unique within its farm"); `services/registry-service/plots.py`

---

## Slide 12: How the assistant worked with me
- Suggestions were recorded next to each decision, in the `Suggested` line
- Two suggestions came from Claude on the web (422 and `200 []`)
- Where I chose differently from the suggestion, the log says so (names, numbers)
- [TODO: one example where I pushed back on the assistant, in my own words]

Speaker notes: The judgment log is the record of who suggested what and what I decided. Be ready to say which suggestions you accepted without change and which you changed. Only write the TODO example from your own experience.

Source: `docs/judgment-log.md` (the `Suggested` lines); `CLAUDE.md` (working rule 9)

---

## Slide 13: Testing
- 115 tests, all passing
- Farms: 26, plots: 56, catalogues: 21, errors: 7, database: 4, schema: 1
- Every endpoint has tests for success and each error case
- A schema test fails if `schema.sql` drifts from the saved course tables

Speaker notes: Name the groups and say what each one covers. The schema test is the reason the course script no longer needs to be read by the tests. The temporary catalogue-only database keeps tests isolated from `registry.db`.

Source: `pytest --collect-only` in `services/registry-service` (115 tests); `services/registry-service/tests/`

---

## Slide 14: Performance check (NFR-1.1)
- Tool: k6 with a fixed rate of 10 requests per second per endpoint
- Data: 100 farms and 10,000 plots, generated by a script
- All 10 GET endpoints pass: 5.7 to 6.2 ms at p95, except list plots at 71.18 ms
- Result: 0% failed requests

Speaker notes: Explain why a fixed rate matters: slow requests can't hide in the numbers. List plots is the one to watch, since it returns all 10,000 plots on every call. Say this is one run on one machine, with the server and the load test on the same computer.

Source: `perf/results/2026-11-07T114657Z_v0.1.0.md`; `perf/nfr_1_1.js`; `perf/seed_perf_db.py`

---

## Slide 15: Reflection
- What worked: decisions logged before use, and tests written with each step
- What I would change: keep one schema source, and measure again after more data
- Known gaps: statuses outside the table use FastAPI's default response, and unhandled `500` errors are not converted
- Still to do: rewrite the log entries in my own words, the service README, and the pull request

Speaker notes: End on the gaps and the next steps, and be open about them. The known gaps are small and don't affect the spec, but I want the instructor to know about them. Say which parts are finished and which are not.

Source: `docs/judgment-log.md`; `services/registry-service/errors.py`; `services/registry-service/README.md` (empty)

---

## Gaps: what I could not find in the repo

- `docs/decisions.md` does not exist. It was renamed to `docs/judgment-log.md`.
- `services/registry-service/README.md` is empty.
- No pull request has been opened yet.
- The judgment-log entries are still the drafts from our conversation. They have not been rewritten in my own words.
- No separate notes on the load test exist. The only record is the results file in `perf/results/`.
- The presentation's pushback example (slide 12) needs your own experience. It is marked TODO.

---

## TODO list

1. Slide 12: write one example, in your own words, where you pushed back on the assistant.
2. Rewrite the judgment-log entries in your own words (the assignment requires at least two).
3. Write the service README at `services/registry-service/README.md`.
4. Open the pull request, with the p95 numbers from the results file.

Slide count: 15.
