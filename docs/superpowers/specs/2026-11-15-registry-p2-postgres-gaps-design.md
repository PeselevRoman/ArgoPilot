# Registry on PostgreSQL: the P2 gaps (design)

Decisions are recorded only in `docs/judgment-log-p2.md`. This file describes the design and does not restate the reasoning. It builds on `2026-11-11-postgres-support-design.md`, which already moved the registry to SQLAlchemy Core and `DATABASE_URL`.

Size: a small change (four contained gaps, no new routes). Short design.

## Intent

`tasks/p2.md` asks the registry to run on PostgreSQL in production and SQLite locally (FR-2.1, NFR-2.1), to be set up from nothing with one command (FR-2.2), and to keep NFR-1.1 on PostgreSQL (NFR-2.2). The code half exists. Four gaps remain.

## Goals

1. **FR-2.2:** one documented command builds the tables in an empty database and loads the 15 seed rows (2 farms, 4 plots, 2 crops, 3 soils, 4 emitters), the same data as `seed_registry.sh`.
2. **NFR-2.2:** p95 of `GET /v1/plots` and `GET /v1/plots/{id}` measured on PostgreSQL at 10 requests per second, recorded in `perf/results/`.
3. Settings are read with pydantic-settings in one `config.py`, as the P2 "Global configurations" section requires.
4. `.claude/settings.json` denies `Read(**/.env)`.

## Non-goals and anti-goals

- No new routes, fields or features. The service still never creates tables itself.
- No Alembic or other migration tool.
- No seed script that can delete data on a database that already has tables.
- No change to the API, its error codes, or `seed_registry.sh` (it keeps working for SQLite).

## Approaches considered (FR-2.2)

- **A. Python seed script** (chosen by the learner): `uv run python seed.py`. Same command on both engines, no `psql` needed, testable in pytest. Cost: the seed rows live in a second place.
- **B. SQL files and `psql`:** no new code, but PostgreSQL only and hard to test.
- **C. Alembic:** the standard for evolving schemas, but new tooling the assignment does not need.

The other three gaps have one sensible way each.

## Design

**Seed script** (`services/registry-service/seed.py`)
- Reads `DATABASE_URL` through `config.py`, builds the engine the way `db.py` does.
- Picks `schema.sql` for SQLite and `schema.postgres.sql` for PostgreSQL, runs it, then inserts the 15 rows with SQLAlchemy Core.
- If the tables already exist, it stops with a clear message and a non-zero exit code. It never drops or overwrites.
- Documented in the README as the one setup command, with the exact PostgreSQL steps (create the database, set `DATABASE_URL`, run the script).
- Tests (SQLite always, PostgreSQL when `TEST_DATABASE_URL` is set): empty database gets 15 rows and the right counts; a second run refuses and changes nothing; the loaded rows match `seed_registry.sh`'s data.

**Config** (`services/registry-service/config.py`)
- A pydantic-settings `Settings` class with `database_url` required, `.env` read from the service folder. A missing value fails at startup with a clear error. An environment variable still wins over `.env`.
- `db.py` uses it instead of python-dotenv. The relative-SQLite-path rule stays in `db.py`. `python-dotenv` leaves `pyproject.toml`, `pydantic-settings` joins it. Existing tests in `test_config.py` keep their meaning and keep passing.

**Performance on PostgreSQL**
- `perf/seed_perf_db.py` and `perf/run_server.py` accept either a SQLite file path or a database URL, and run with the service's Python. The dataset (100 farms, 10,000 plots, fixed random seed) goes into a separate database, `registry_perf`.
- Rebuilding a PostgreSQL perf database drops and recreates its tables, so the script refuses unless the database name contains `perf` (the same guard idea as the `test` rule).
- The k6 script is unchanged. The result is added to `perf/results/` and the registry README, with the SQLite numbers beside it. Performance checks stay outside the test suite.

**`.claude/settings.json`:** `{ "permissions": { "deny": ["Read(**/.env)"] } }` in the project root.

## Constraints

- Every code change has tests (CLAUDE.md rule 4). Values that change between environments are in `.env`, and `.env.example` stays complete.
- The local PostgreSQL has the databases `registry` and `registry_test`. `registry_perf` still has to be created by the learner with `sudo`.
- If p95 on PostgreSQL exceeds 100 ms, that is a finding to report and fix, not to hide.

## Left to the builder

- Layout inside `seed.py` (data as Python constants, helper names).
- How the multi-statement schema file is executed on each driver.
- Exact wording of the refusal messages and the README text.

## Decisions to log (pending the learner's confirmation)

1. Seed command is a Python script using SQLAlchemy, not `psql` or Alembic.
2. The seed script refuses a database that already has tables.
3. PostgreSQL performance data lives in a separate `registry_perf` database, with a name guard.
