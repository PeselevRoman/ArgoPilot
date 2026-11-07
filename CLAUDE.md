# AgroPilot

Course project: building the AgroPilot registry API as a backend engineer who uses AI. The learner is an experienced C# / Unity developer who is new to Python backend work and to AI. Explain backend and AI concepts when they first appear, and connect them to C# and game development where that helps.

## Current assignment

Assignment: `tasks/p1_registry_api.md`. Read it fully before doing anything. It is the source of truth for requirements, routes, error codes, and data.

Work happens in `services/registry-service`. Its tests go in `services/registry-service/tests/`.

Layout:
- `tasks/`: the assignment, and the course's `seed_registry.sh` (course material, left unchanged)
- `services/registry-service/`: the service code, its README, `schema.sql` (table definitions for the test database), `seed_registry.sh` (a copy of the course script, used to create `registry.db`), and `tests/`
- `perf/`: the performance check (k6 script, launcher, dataset script, and `results/`)
- `docs/judgment-log.md`: the learner's judgment log (renamed from `docs/decisions.md`)
- `docs/presentation/`: the presentation content

## Stack (decided)

- Python
- FastAPI for the HTTP API
- SQLite (`registry.db`), created by `services/registry-service/seed_registry.sh`. The test database is built from `schema.sql`.
- pytest for tests (dev dependency)
- httpx2 for the test client (dev dependency)
- uv for dependencies
- k6 for the load test (installed outside `uv`)

All decisions are recorded in `docs/judgment-log.md` and only there. Check it for the latest decisions and do not change them without asking.

## Working rules

1. Before starting any step, restate what you understand and wait for the learner to confirm. Ask when something is ambiguous.
2. For every choice, name the approach, explain why it fits, and mention common alternatives and trade-offs.
3. Label each recommendation as industry consensus or personal judgment. Flag advice that may go stale, since AI tooling changes quickly.
4. Every code change includes tests. Test scope: unit tests for validation rules, API tests for every endpoint and error case, a few database tests for uniqueness and delete rules. Performance checks stay separate from the test suite.
5. Build only what the spec lists. Do not add routes, fields, or features outside the spec.
6. Return only the fields listed in the spec's data section.
7. Every error response uses `application/problem+json` with a `code` of `VALIDATION`, `NOT_FOUND`, `CONFLICT`, or `UNAVAILABLE`.
8. Make small, reviewable commits. Record every decision only in `docs/judgment-log.md`, and nowhere else.
9. When a decision comes up, suggest logging it and propose the entry wording. The learner confirms or denies. Only after confirmation does the assistant write the entry in `docs/judgment-log.md`. The learner may also start an entry on their own. Never log a decision without confirmation.
10. The learner owns the code. Explain each file as it is created.
