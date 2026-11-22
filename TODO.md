# AgroPilot: TODO

Ideas that reach across services. They are **out of scope for P2**. Ideas for one service are in that service's own `TODO.md`, for example [`services/planner-service/TODO.md`](services/planner-service/TODO.md).

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

## 4. Find out why `GET /v1/plots` is slow, and decide whether to page it

**Now:** in the PostgreSQL run with 10,000 plots (`perf/results/2026-11-21T173455Z_v0.1.0.md`), `GET /v1/plots` has p95 81.6 ms. Every other registry endpoint is under 10 ms, and the target is 100 ms. It is the closest to failing, and it grows with the number of plots. The registry has no `limit`, `offset` or paging, so the list probably returns all 10,000 plots in one response. That cause is a hypothesis: nobody has profiled it. The frontend does not appear to call this endpoint for a plot page, so it is not on the grower's main path.

**Find out first:**
- Check the size of the response, the time of the SQL query alone, and the time to build and serialise the JSON, to see which part is slow.

**Then, if it needs fixing:**
- Add paging (for example `limit` and `offset`, or a cursor). The routes and response fields are fixed by the assignments, so this is a new decision for the judgment log, and a change to a list response would break callers that expect every plot.
- Or filter by a field that already exists, if the assignment's contract allows it. Check the assignments before choosing.
- Re-run the registry's performance check and record the new p95 and the dataset size.
