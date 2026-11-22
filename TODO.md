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
