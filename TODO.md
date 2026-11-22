# AgroPilot: TODO

Ideas that reach across services. They are **out of scope for P2**, except item 5, which is a checklist for finishing P2. Ideas for one service are in that service's own `TODO.md`, for example [`services/planner-service/TODO.md`](services/planner-service/TODO.md).

## 1. Contract tests, so a changed response format is caught before runtime

**Now:** every service is tested against a fake of the services it calls (never a real network, as the working rules require). The fakes are written by hand, so nothing checks that they match what the real service sends. If registry-service renames `lat` to `latitude`, the planner's tests still pass against the old fake, and the failure shows up only at runtime as `503 UPSTREAM_UNAVAILABLE` (see "An invalid or non-finite upstream answer makes the plan unavailable" in `docs/judgment-log-p2.md`).

**Make it checked:**
- Write the shape of each answer once, for example as a JSON Schema file for the plot, soil, emitter and forecast answers and for the plan.
- In the provider service's tests, check that the real answers match the schema. In the caller's tests, check that the fake's answers match the same schema. A format change then fails a test in both places.
- The pairs to cover: planner and registry, planner and weather, frontend and planner, and frontend and registry.
- Services must still never import each other's code, so the schema files need a home outside any one service (for example a `contracts/` folder at the repository root), or each service keeps a copy that a script compares.
- This is a new test layer and a new folder, so it needs a decision on where the schemas live and who owns them. It is outside P2's scope.

## 2. A performance run for the planner

**Now:** the registry (NFR-2.2) and the weather cache hit (NFR-2.3) have performance runs in `perf/results/`. The planner has none. A plan makes up to four upstream calls (the plot first, then soil, emitter and forecast at the same time), so its latency is at least two round trips plus the slowest of the three. Nobody has measured it, so any statement about the planner's speed is a guess from reading the code.

**Measure it:**
- Add a k6 script and launcher for `GET /v1/plots/{id}/plan` in `perf/`, next to the registry's and weather's, with the same recorded result file. Performance checks stay separate from the test suite.
- Run it against the real registry (PostgreSQL, 10,000 plots) and the real weather service with a warm cache, at 10 requests per second, and record p95.
- Decide the target first: the assignment gives none for the planner, so any number is a new decision for the judgment log.
- Record where the time goes (the plot call, the parallel calls, the engine), not only the total.

## 3. Measure the weather service when the cache is empty or the provider is slow

**Now:** the 2.3 ms p95 is for a fresh forecast with a fake provider. A cache miss waits for Open-Meteo, and after three failed attempts the worst case is about 16 s (3 × 5 s timeout plus 2 × 0.5 s waits). That figure is calculated from the settings, not measured. The planner waits up to 45 s for it.

**Measure it:**
- Run the weather service with a fake provider that answers slowly, fails, or times out, and record how long a request takes in each case.
- Check what many requests for the same new cell cost, to confirm they share one fetch (see "Concurrent requests for one cell share a single provider fetch" in `docs/judgment-log-p2.md`).
- Check that the planner's 45 s timeout and the weather service's retries really fit together, with a request that goes through the whole chain.

## 4. A traceability matrix from each requirement to its test

**Now:** `tasks/p2.md` lists FR-2.1 to FR-2.19 and NFR-2.1 to NFR-2.8 (NFR-2.5 was removed). Each plan in `docs/superpowers/plans/` has a "Spec coverage" section that maps requirements to the tasks that build them, but nothing maps a requirement to the test, or the performance run, that proves it. Test names describe behaviour and do not carry the requirement's number. Asked "show me the test for FR-2.14", someone has to search for it. A requirement with no test, or a test that no longer matches its requirement, would not be noticed.

**Make it checkable:**
- Write a table, in one place (for example `docs/traceability.md`), with one row per requirement: its number, the test file and test names (or the k6 run, or the manual check) that cover it, and how it is verified (automated, measured, or by hand).
- Some requirements are verified by hand, not by a test, for example NFR-2.8 (the 375 px layout, checked on 2026-11-21). The table must say so, so a manual check is not mistaken for an automated one.
- Keep it from going stale: either a short script that reads a requirement number from each test (a marker or a comment such as `FR-2.14`) and fails when a requirement has none, or accept that the table is updated by hand with each change. The script is more work but is the only version that notices a gap.
- Decide whether it covers earlier assignments. P1's requirements are in `tasks/p1_registry_api.md`, and P2 overrides some of them.

## 5. Checklist before the P2 presentation

Not an idea for the product: things to do or confirm before presenting. Tick them off, then delete this item.

- [ ] Run `scripts/check.sh` with `TEST_DATABASE_URL` set to a database named like `registry_test`, so the registry suite runs on PostgreSQL as well as SQLite (NFR-2.1). A plain run covers SQLite only.
- [ ] Check the current Open-Meteo limits on its website. The capacity estimate given in conversation (about 10,000 calls per day, roughly 1,250 active cells) was from memory and may be out of date.
- [ ] Remember which numbers are calculated and which are measured. The 16 s worst case for one weather request comes from the settings and was never measured. The measured ones are in `perf/results/`.
- [ ] Say which checks are manual: the 375 px layout (NFR-2.8, passed on 2026-11-21) and the run of the real services together.
- [ ] Push the commits made since the last push (the TODO files, the judgment-log entries and the README change). Pushing and opening the pull request are done by you, after asking.
- [ ] Open the P2 pull request, with the measured numbers and the skills used in its description.
