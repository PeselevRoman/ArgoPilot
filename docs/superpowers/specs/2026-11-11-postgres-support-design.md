# PostgreSQL support: design

Decisions are recorded only in `docs/judgment-log.md`, section "PostgreSQL support". This file describes the design and points to those entries by title. It does not restate their reasoning.

## Goal

The registry service runs on SQLite (`registry.db`) locally and in tests, and on an existing PostgreSQL database in production. `DATABASE_URL` selects the engine. The 16 existing endpoints behave exactly as before: same status codes, same `application/problem+json` errors and codes, same `Retry-After` on `503`.

## Scope

In scope:
- Reading `DATABASE_URL` from the environment or `.env`.
- Replacing direct `sqlite3` use with SQLAlchemy Core in `db.py`, `farms.py`, `plots.py`, `catalogues.py`.
- `schema.postgres.sql`, `.env.example`, new dependencies, tests, README update.

Out of scope:
- Any new route, field or feature.
- Creating tables from the service (it never does).
- Migrating existing data, or a Postgres performance run (follow-up).
- Docker or CI.

## Judgment log entries this design follows

- Postgres uses native column types
- SQLAlchemy Core talks to both databases
- DATABASE_URL has no default
- Tests run on SQLite, plus on PostgreSQL when one is available
- A database connection failure returns 503
- PostgreSQL gets its own schema file
- Malformed ids behave as before; UUID text is accepted in any form
- Catalogue ids sort by byte order on PostgreSQL

Anyone implementing this design reads the whole "PostgreSQL support" section of the log first. It holds the reasoning and trade-offs behind each choice.

## Components

- `db.py` (rewritten): loads `.env`, reads `DATABASE_URL` (startup error if missing), builds one SQLAlchemy engine. The connection dependency is `db.get_connection` and the annotated type is `db.Conn`; `get_db`, `DB_PATH` and `DbConnection` are removed. One transaction per request, committed before the response is sent, rolled back on error. SQLite: file-exists check and foreign keys switched on. Connection failures become `503` with `Retry-After: 5` and the underlying error is logged.
- `tables.py` (new): the five tables as SQLAlchemy `Table` objects with a custom `UuidId`, `Date` and `Float` types. The service never calls `create_all`.
- `farms.py`, `plots.py`, `catalogues.py`: raw SQL becomes query-builder calls. Pydantic models, validation and messages are unchanged. `IntegrityError` from SQLAlchemy replaces `sqlite3.IntegrityError`. Ids are returned to clients as strings.
- A small id helper parses a string as a UUID and returns nothing when it is malformed.
- `schema.postgres.sql` (new): native types, `uuid` for farm and plot ids and `plots.farm_id`, `date`, `double precision`; catalogue ids stay `text`.
- `.env.example` (new): `DATABASE_URL=sqlite:///registry.db`.
- `pyproject.toml`: add `sqlalchemy`, `psycopg[binary]`, `python-dotenv`.

## Behavior

Request flow is unchanged: one connection and one transaction per request.

| Situation | Result |
| --- | --- |
| Cannot connect (either engine), SQLite file missing | `503 UNAVAILABLE`, `Retry-After: 5` |
| Unique or foreign key violation | handled as today (`409` or `422`, else re-raised) |
| Other database errors, such as missing tables | not converted (`500`) |
| Malformed path id | `404` |
| Malformed body `farm_id` | `422 Unknown farm` |
| `GET /v1/plots?farm_id=<malformed>` | `200 []` |

Known difference: a UUID in uppercase or without hyphens now finds its row. Everything else is identical.

Lists sort by `id`. SQLite sorts text by bytes, Postgres by locale, so catalogue ids in the Postgres schema use byte-order collation (see the log entry above).

## Testing

- All existing API and database tests pass unchanged on SQLite. Only the `test_db` fixture changes: it sets `DATABASE_URL`.
- The same tests also run on Postgres when `TEST_DATABASE_URL` is set, and are skipped otherwise. The fixture loads `schema.postgres.sql`, seeds the catalogues, and refuses to run unless the database name contains `test`.
- New tests that need no Postgres server: missing `DATABASE_URL` fails at startup; `.env` is read; a Postgres URL on a closed port gives `503` with `Retry-After`; `schema.postgres.sql` and `schema.sql` have the same tables and column names; malformed-id behavior on both engines.
- Performance checks stay outside the test suite.

Until a Postgres is available, the Postgres path is only partly verified (the 503 and schema parity tests). Reports must say so.

## Amendments found while planning

1. SQLAlchemy's built-in `Uuid` stores 32-character hex without hyphens on SQLite. Existing `registry.db` rows have hyphenated ids, so lookups would fail. A custom `UuidId` type is used instead.
2. On PostgreSQL a failed statement aborts the whole transaction, so the recheck after `IntegrityError` in `create_plot`, `update_plot` and `delete_farm` would fail. The code calls `conn.rollback()` before the recheck. This is safe because the failing write is the only write in the request.
3. More tests change than just the `test_db` fixture: tests that touch `sqlite3` directly or patch `db.DB_PATH` are edited.
4. `perf/run_server.py` sets `db.DB_PATH`, so it changes too. A relative SQLite path in `DATABASE_URL` resolves against the service folder (the existing "database path is resolved from the code's location" decision), and `.env` is read from that folder.
5. The statement that `get_db` and `DbConnection` keep their names is superseded. The old names (`get_db`, `DB_PATH`, `DbConnection`) are removed, and the connection dependency is `db.get_connection` with the annotated type `db.Conn`.

## Open items

- Postgres p95 measurement: follow-up, needs a real Postgres.
- Whether to install Postgres in WSL: the learner decides when the plan is made.
