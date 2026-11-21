# AgroPilot

Course project: building AgroPilot, a set of small services, as a backend engineer who uses AI. The learner is an experienced C# / Unity developer who is new to Python backend work and to AI. Explain backend and AI concepts when they first appear, and connect them to C# and game development where that helps.

## Assignments

The assignments are in `tasks/`, one file per assignment (`p1_registry_api.md`, `p2.md`, and so on). The newest one is the current assignment. Read it fully before doing anything. It is the source of truth for requirements, routes, error codes, and data.

Where the current assignment disagrees with an earlier one, the current one wins. The same applies to this file: where an assignment disagrees with it, the assignment wins, and the difference is logged in that assignment's judgment log.

## Layout

- `tasks/`: the assignments, and the course's `seed_registry.sh` (course material, left unchanged)
- `services/<name>/`: one folder per service. Each has its own code, `.venv`, `.env` (never committed), `.env.example` (committed), `README.md`, and `tests/`. Services never import each other's code. They talk over HTTP only.
- `scripts/`: `dev.sh` (start everything), `check.sh` (run every check) and their tests. Development helpers, not part of a service.
- `perf/`: the registry's performance check (k6 script, launcher, dataset script, and `results/`). A later service keeps its own performance check next to it.
- `docs/judgment-log.md`: the judgment log of P1. `docs/judgment-log-pN.md`: the log of assignment N, for example `docs/judgment-log-p2.md`.
- `docs/superpowers/`: design documents and plans written by the Superpowers skills
- `docs/presentation/`: the presentation content

Registry-specific details, such as its tables, schema files and seed script, are in `services/registry-service/README.md`.

## Stack (decided)

Shared by the Python services:

- Python, with FastAPI for the HTTP API
- uv for dependencies
- pytest for tests, and httpx2 for the test client (dev dependencies)
- pydantic-settings for configuration, in one `config.py` per service

Per service, as the assignments add them:

- registry-service: SQLAlchemy Core on SQLite (local) or PostgreSQL (production), chosen by `DATABASE_URL`
- weather-service and planner-service: httpx for calls to other services
- frontend: Node.js and Next.js

Installed outside `uv`: k6 (load tests), Node.js, and PostgreSQL.

## Decisions

Every assignment has its own judgment log. Decisions go only in the current assignment's log, and nowhere else. Earlier logs are no longer added to. Before deciding anything, check all the logs, newest first. Do not change a decision without asking. If a new decision overrides an older one, the new entry says so.

When a new assignment starts, propose the new log file and wait for the learner to confirm.

## Error responses

Every error response uses `application/problem+json` (RFC 9457) with a `code` of `VALIDATION`, `NOT_FOUND`, `CONFLICT`, `UNAVAILABLE`, or `UPSTREAM_UNAVAILABLE`. A service uses `UNAVAILABLE` when its own dependency fails, and `UPSTREAM_UNAVAILABLE` when another AgroPilot service it calls has failed. Details are in `docs/judgment-log-p2.md`.

## Working rules

1. Before starting any step, restate what you understand and wait for the learner to confirm. Ask when something is ambiguous. When a Superpowers skill is in use, its steps and approval gates apply in addition to this rule.
2. For every choice, name the approach, explain why it fits, and mention common alternatives and trade-offs.
3. Label each recommendation as industry consensus or personal judgment. Flag advice that may go stale, since AI tooling changes quickly.
4. Every code change includes tests. Test scope: unit tests for validation rules, API tests for every endpoint and error case, a few database tests for uniqueness and delete rules. For a service that calls other services, replace the upstream service with a fake in tests, and never use a real network. Performance checks stay separate from the test suite.
5. Build only what the current assignment's spec lists. Do not add routes, fields, or features outside it.
6. Return only the fields the spec lists for each resource.
7. Make small, reviewable commits. Work for each assignment is on its own branch (`p2` for P2), and ends in a pull request. Never push, or open a pull request, without asking.
8. Record every decision only in the current assignment's judgment log. Design documents and plans are working documents: they may describe a decision, but the judgment log is where it is recorded.
9. When a decision comes up, suggest logging it and propose the entry wording. The learner confirms or denies. Only after confirmation does the assistant write the entry in the current judgment log. The learner may also start an entry on their own, including one about how the project is run. Never log a decision without confirmation.
10. The learner owns the code. Explain each file as it is created.
11. Never read `.env` files. Keep `.env.example` complete and current, with safe example values. Every value that can change between environments is configuration in `.env`, not in code.
12. Irrigation numbers are calculated only by the planner's engine, following the `irrigation-calc-reference` skill. No AI model computes or adjusts them. Cite the source for every domain claim.
