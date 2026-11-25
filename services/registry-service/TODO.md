# registry-service: TODO

Ideas for the final product. They are **out of scope for P2**. Ideas that reach across services are in the root [`TODO.md`](../../TODO.md).

## 1. Find out why `GET /v1/plots` is slow, and decide whether to page it

**Now:** in the PostgreSQL run with 10,000 plots (`perf/results/2026-11-21T173455Z_v0.1.0.md`), `GET /v1/plots` has p95 81.6 ms. Every other registry endpoint is under 10 ms, and the target is 100 ms. It is the closest to failing, and it grows with the number of plots. The registry has no `limit`, `offset` or paging, so the list probably returns all 10,000 plots in one response. That cause is a hypothesis: nobody has profiled it.

**It is on the main path.** The frontend's home page (`listFarmsWithPlots` in `services/frontend/src/lib/registry.ts`) calls `GET /v1/farms` and `GET /v1/plots` on every load, then groups the plots by farm in the frontend. So every visitor pays for the full list, and the home page is the first thing a grower sees. The list route has no filter, so the frontend cannot ask for one farm's plots.

**Find out first:**
- Check the size of the response, the time of the SQL query alone, and the time to build and serialise the JSON, to see which part is slow.

**Then, if it needs fixing:**
- Add paging (for example `limit` and `offset`, or a cursor), or a filter by farm (for example `?farm_id=`), so the home page can ask for what it shows. The routes and response fields are fixed by the assignments, so either is a new decision for the judgment log, and changing a list response could break callers that expect every plot.
- Change the frontend to use it, and re-run the registry's performance check, recording the new p95 and the dataset size.
