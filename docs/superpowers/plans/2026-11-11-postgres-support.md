# PostgreSQL Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The registry service runs on SQLite or PostgreSQL, chosen by `DATABASE_URL`, with all 16 endpoints behaving exactly as before.

**Architecture:** `db.py` builds a SQLAlchemy engine from `DATABASE_URL` and hands each request one connection and one transaction. Routes use SQLAlchemy Core queries on `Table` objects in `tables.py`. A custom `UuidId` column type keeps ids as hyphenated text in SQLite and native `uuid` in Postgres. Routes migrate one file at a time while the old `sqlite3` dependency still exists, so the suite stays green after every task. The last task removes the old code.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x Core, `psycopg[binary]` (psycopg 3), `python-dotenv`, pytest, uv.

**Spec:** `docs/superpowers/specs/2026-11-11-postgres-support-design.md`. Read the whole "PostgreSQL support" section of `docs/judgment-log.md` before starting: it holds the reasoning and trade-offs behind every choice. Do not add decisions anywhere except that log. If you hit a decision the log does not cover, stop and report it.

## Spec amendments found while planning

The spec is wrong or silent on four points. Task 7 applies these to the spec file; the plan already follows them.

1. SQLAlchemy's built-in `Uuid` stores 32-character hex without hyphens on SQLite. Existing `registry.db` rows have hyphenated ids, so lookups would fail. The plan uses a custom `UuidId` type instead.
2. On Postgres a failed statement aborts the whole transaction, so the "recheck after `IntegrityError`" code in `create_plot`, `update_plot`, `delete_farm` would fail. The plan calls `conn.rollback()` before the recheck. This is safe because the failing write is the only write in the request.
3. More tests change than just the `test_db` fixture: tests that touch `sqlite3` directly or patch `db.DB_PATH` are edited.
4. `perf/run_server.py` sets `db.DB_PATH`, so it changes too. A relative SQLite path in `DATABASE_URL` resolves against the service folder (the existing "database path is resolved from the code's location" decision), and `.env` is read from that folder.

## Global Constraints

- Work in `services/registry-service`; run everything from there: `uv run pytest -q`.
- Build only what the spec lists: no new routes, fields or features. The service never creates tables (`create_all` is not called).
- Every error response is `application/problem+json` with code `VALIDATION`, `NOT_FOUND`, `CONFLICT` or `UNAVAILABLE`. `503` carries `Retry-After: 5`.
- Responses return only the spec's data fields; ids are JSON strings.
- Postgres column types: `uuid` (farm id, plot id, `plots.farm_id`), `date` (`planting_date`), `double precision` (floats), `integer` (`available_water_mm_per_m`), `text` (everything else, including catalogue ids with `COLLATE "C"`).
- `DATABASE_URL` has no default: missing or empty fails at startup.
- Postgres tests run only when `TEST_DATABASE_URL` is set, and refuse any database whose name does not contain `test`.
- Commit messages end with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Tests and docs: explain each new file to the learner as it is created (project rule).

## Review Focus

Most likely to bite, each pinned by a test in the owning task:

1. Seeded `registry.db` rows (hyphenated ids) must stay readable, updatable and deletable. (Task 1, Task 5)
2. Malformed ids: path `404`, body `farm_id` `422 Unknown farm`, `?farm_id=garbage` `200 []`. (Task 5, Task 6)
3. A relative SQLite URL works when the server starts from another folder. (Task 2)
4. Empty `DATABASE_URL`, unsupported scheme, and plain `postgresql://` (no driver name) behave sensibly. (Task 2)
5. Creating a plot with no `ignore_id` must not break the uuid comparison in the name check. (Task 6)

## File Structure

- `db.py` (rewrite): URL, engine, connection dependency, 503 mapping.
- `tables.py` (new): `UuidId` type and the five `Table` objects.
- `ids.py` (new): `parse_uuid`.
- `catalogues.py`, `farms.py`, `plots.py`: queries rewritten, models unchanged.
- `main.py`: startup check.
- `schema.postgres.sql`, `.env.example` (new).
- `tests/conftest.py` (rewrite), `tests/catalogues_seed.sql` (new), `tests/test_*.py` (edited), `tests/test_config.py`, `tests/test_types.py`, `tests/test_schema_parity.py` (new).
- `perf/run_server.py`, `README.md`: updated in Task 7.

---

### Task 1: Dependencies, id helper and column types

**Files:**
- Modify: `pyproject.toml` (via `uv add sqlalchemy "psycopg[binary]" python-dotenv`)
- Create: `ids.py`, `tables.py`, `tests/test_types.py`

**Interfaces:**
- Produces: `ids.parse_uuid(value: str) -> uuid.UUID | None` (returns `None` when malformed; accepts upper case, no hyphens, braces).
- Produces: `tables.UuidId` (`TypeDecorator`; Python value `uuid.UUID`; SQLite stores lowercase hyphenated TEXT; Postgres native `uuid`).
- Produces: `tables.metadata`, and `tables.farms`, `crops`, `soils`, `emitters`, `plots` (`sqlalchemy.Table`) with the same columns, foreign keys and `UNIQUE (farm_id, name)` as `schema.sql`. Types: `UuidId` for `farms.id`, `plots.id`, `plots.farm_id`; `Date` for `planting_date`; `Double` for floats; `Integer`; `Text` otherwise.

- [ ] **Step 1: Write failing tests in `tests/test_types.py`** (in-memory SQLite engine, `metadata.create_all` is allowed in tests only)
  - `test_parse_uuid_accepts_any_uuid_form`: lowercase, uppercase, no-hyphen and `{braces}` all return the same `UUID`.
  - `test_parse_uuid_returns_none_for_malformed_text`: `""`, `"garbage"`, `"b7e2c0a0"`, `"some-id"` return `None`.
  - `test_uuid_is_stored_as_hyphenated_text_on_sqlite`: insert a farm with `UUID("b7e2c0a0-3c1d-4f0a-9a11-0c5d2e6f1001")`; `SELECT id FROM farms` through raw SQL returns the exact string `"b7e2c0a0-3c1d-4f0a-9a11-0c5d2e6f1001"`.
  - `test_existing_hyphenated_row_can_be_read_and_filtered`: insert that string with raw SQL; `select(farms).where(farms.c.id == UUID(...))` returns the row, and `row.id` is a `UUID`.
  - `test_date_round_trips_as_iso_text`: a plot's `planting_date` of `date(2026, 3, 1)` is stored as `"2026-03-01"` and read back as `date(2026, 3, 1)`.

- [ ] **Step 2: Run** `uv run pytest tests/test_types.py -q`. Expected: FAIL (modules missing).

- [ ] **Step 3: Implement `ids.py` and `tables.py`** as specified above. `UuidId.load_dialect_impl` returns `postgresql.UUID(as_uuid=True)` on the `postgresql` dialect and `Text()` otherwise; `process_bind_param` returns the `UUID` for Postgres and `str(value)` otherwise; `process_result_value` returns a `UUID` in both cases; set `cache_ok = True`. Add a short comment on why built-in `Uuid` is not used (hex without hyphens on SQLite).

- [ ] **Step 4: Run** `uv run pytest -q`. Expected: all pass (the old suite is untouched).

- [ ] **Step 5: Commit** `git add pyproject.toml uv.lock ids.py tables.py tests/test_types.py` with message "Add SQLAlchemy dependencies, id parsing and table definitions".

---

### Task 2: New database connection layer (alongside the old one)

**Files:**
- Modify: `db.py` (add the new API; leave `get_db`, `DB_PATH`, `DbConnection` as they are for now)
- Create: `.env.example`, `tests/test_config.py`
- Modify: `tests/test_db.py` (add tests for the new dependency; keep the old ones)

**Interfaces:**
- Consumes: `DATABASE_URL` environment variable.
- Produces:
  - `db.ENV_FILE: Path` (`.env` in the service folder) and `db.load_env_file(path: Path = ENV_FILE) -> None` (python-dotenv, `override=False`); called once at import.
  - `db.get_database_url() -> str`: reads `DATABASE_URL`; raises `RuntimeError` when missing, empty, or its backend is not `sqlite` or `postgresql`.
  - `db.get_engine() -> sqlalchemy.Engine`: one cached engine per URL. A relative SQLite file path resolves against the service folder; `postgresql://` and `postgres://` are rewritten to `postgresql+psycopg://`; SQLite engines turn `PRAGMA foreign_keys = ON` on at each connect.
  - `db.reset_engines() -> None`: disposes and clears all cached engines (tests use it).
  - `db.get_connection() -> Iterator[sqlalchemy.Connection]` and `db.Conn = Annotated[Connection, Depends(get_connection, scope="function")]`. One transaction per request: commit when the route succeeds (before the response is sent), roll back on error, always close. A SQLite file that does not exist, or any `sqlalchemy.exc.OperationalError` while connecting, becomes `HTTPException(503, "Database unavailable", headers={"Retry-After": "5"})`; the underlying error is logged with `logging.getLogger("registry.db")`.
- `.env.example` contains `DATABASE_URL=sqlite:///registry.db` with a one-line comment showing the Postgres form `postgresql://user:password@host:5432/dbname`.

- [ ] **Step 1: Write failing tests**
  - `tests/test_config.py`:
    - `test_missing_database_url_raises`, `test_empty_database_url_raises`, `test_unsupported_scheme_raises` (`mysql://x`): `pytest.raises(RuntimeError)` with a message that names `DATABASE_URL`.
    - `test_env_file_is_read(tmp_path, monkeypatch)`: write `DATABASE_URL=sqlite:///x.db` to a temp `.env`; `monkeypatch.delenv` first; after `load_env_file(path)`, `get_database_url() == "sqlite:///x.db"`.
    - `test_env_variable_wins_over_env_file`: variable already set stays unchanged.
    - `test_plain_postgresql_url_uses_the_psycopg_driver`: `get_engine().dialect.driver == "psycopg"` for `postgresql://u:p@127.0.0.1:1/t` (no connection is made).
    - `test_relative_sqlite_path_resolves_from_the_service_folder(monkeypatch, tmp_path)`: `monkeypatch.chdir(tmp_path)`; for `sqlite:///registry.db`, `get_engine().url.database == str(Path(db.__file__).parent / "registry.db")`.
  - `tests/test_db.py` (new probe app using `db.Conn`):
    - `test_new_dependency_returns_503_with_retry_after_when_sqlite_file_is_missing`.
    - `test_new_dependency_returns_503_when_postgres_is_unreachable`: URL `postgresql://u:p@127.0.0.1:1/test`; expects `503`, `Retry-After: 5`, and the same for a log record on `registry.db` (use `caplog`).
    - `test_new_dependency_turns_foreign_keys_on`: `text("PRAGMA foreign_keys")` returns `1`.
    - `test_new_dependency_discards_writes_when_the_route_fails`: mirror of the existing rollback test.
    - `test_new_dependency_commits_before_the_response_returns`: write in a route, then a second request sees it.
  - Add an autouse fixture in `tests/conftest.py` that does `monkeypatch.delenv("DATABASE_URL", raising=False)` before each test and calls `db.reset_engines()` after, so a developer's real `.env` never leaks into tests.

- [ ] **Step 2: Run** `uv run pytest tests/test_config.py tests/test_db.py -q`. Expected: FAIL (functions missing).

- [ ] **Step 3: Implement** the interfaces above in `db.py`. Create `.env.example`.

- [ ] **Step 4: Run** `uv run pytest -q`. Expected: all pass.

- [ ] **Step 5: Commit** "Add DATABASE_URL-driven engine and connection dependency".

---

### Task 3: Test harness for both engines, and the Postgres schema file

**Files:**
- Create: `schema.postgres.sql`, `tests/catalogues_seed.sql`, `tests/test_schema_parity.py`
- Modify: `tests/conftest.py`, `tests/test_farms.py`, `tests/test_plots.py` (and any other test that calls `sqlite3.connect(test_db)`; find them with `grep -rn "sqlite3" tests`)

**Interfaces:**
- Produces: fixture `test_db`, parametrized with ids `sqlite` and `postgres`, returning a `TestDatabase` object:
  - `.url: str`, `.engine: sqlalchemy.Engine`
  - `.execute(sql: str, **params) -> None` runs one statement and commits (SQL uses `:name` parameters).
  - `.fetch_all(sql: str, **params) -> list[tuple]`.
- Behavior: the `sqlite` variant builds the file with `tests/seed_test_db.sh` as today. The `postgres` variant is skipped unless `TEST_DATABASE_URL` is set; it refuses a database whose name does not contain `test` (`pytest.fail` with a clear message), drops the five tables if present, runs `schema.postgres.sql`, then `tests/catalogues_seed.sql` (same rows as `seed_test_db.sh`). Both variants `monkeypatch.setenv("DATABASE_URL", url)`. **Transitional:** the `sqlite` variant also sets `db.DB_PATH` so unmigrated routes keep working; Task 7 removes that line.
- `schema.postgres.sql`: same five tables as `schema.sql`, native types as in Global Constraints, `COLLATE "C"` on `crops.id`, `soils.id`, `emitters.id` and every column that references them (`plots.crop_id`, `plots.soil_id`, `plots.emitter_id`), same foreign keys, `UNIQUE (farm_id, name)`. Header comment says: run once on the production database before release; the service never runs it.

- [ ] **Step 1: Write failing tests**
  - `tests/test_schema_parity.py::test_both_schema_files_have_the_same_tables_and_columns`: parse table names and column names from `schema.sql` and `schema.postgres.sql` (regex over `CREATE TABLE name ( ... );`, skipping constraint lines that start with `UNIQUE`, `PRIMARY`, `FOREIGN`, `CONSTRAINT`); assert equal dicts of `{table: [columns in order]}`. Assert a failure message names the table that differs.
  - `test_postgres_schema_uses_the_native_types`: text assertions on `schema.postgres.sql` for `uuid`, `date`, `double precision` and `COLLATE "C"`.
  - In `tests/test_farms.py`, replace the three direct `sqlite3.connect(test_db)` blocks (`test_create_is_saved_before_the_response_returns` and the two delete-409 tests) with `test_db.fetch_all` / `test_db.execute`, using `:name` parameters and `uuid.UUID(...)` values where the column is a uuid. Do the same for any other direct `sqlite3` use in the tests.

- [ ] **Step 2: Run** `uv run pytest -q`. Expected: parity tests FAIL (file missing); the rewritten farm tests still PASS on the `sqlite` variant; the `postgres` variant shows as skipped.

- [ ] **Step 3: Implement** the files and fixture above.

- [ ] **Step 4: Run** `uv run pytest -q`. Expected: all pass; every `test_db` test appears twice (`[sqlite]` passed, `[postgres]` skipped).

- [ ] **Step 5: Commit** "Add Postgres schema file and a test fixture for both engines".

---

### Task 4: Catalogue routes on SQLAlchemy

**Files:** Modify `catalogues.py`; modify `tests/test_catalogues.py`.

**Interfaces:**
- Consumes: `db.Conn`, `tables.crops`, `soils`, `emitters`.
- Produces: unchanged routes and models (`Crop`, `Soil`, `Emitter`).

- [ ] **Step 1: Update the 503 test** in `tests/test_catalogues.py` to `monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'missing.db'}")` in place of patching `db.DB_PATH`. Add `test_lists_are_sorted_by_id`: crops are `bell-pepper, tomato`; soils `clay-loam, loam, sand`; emitters `dripnet-pc-0.6, -1.0, -1.6, -2.0` (all existing tests already run on both engines through `test_db`).
- [ ] **Step 2: Run** `uv run pytest tests/test_catalogues.py -q`. Expected: the 503 test FAILS (catalogue routes still read the old path).
- [ ] **Step 3: Rewrite the six queries** with `select(...)`, `.order_by(table.c.id)`, `conn.execute(...).mappings()`, and `Model.model_validate(dict(row))`. Replace the `DbConnection` import with `Conn`.
- [ ] **Step 4: Run** `uv run pytest -q`. Expected: all pass.
- [ ] **Step 5: Commit** "Move catalogue routes to SQLAlchemy".

---

### Task 5: Farm routes on SQLAlchemy

**Files:** Modify `farms.py`; modify `tests/test_farms.py`.

**Interfaces:**
- Consumes: `db.Conn`, `tables.farms`, `tables.plots`, `ids.parse_uuid`.
- Produces: unchanged routes and models. Helper signatures: `get_farm_or_404(conn: Connection, farm_id: str) -> Farm` (malformed id raises the same `404`), `farm_has_plots(conn: Connection, farm_id: UUID) -> bool`.

- [ ] **Step 1: Add tests** to `tests/test_farms.py`
  - `test_get_with_a_malformed_id_returns_404_not_found` for `GET`, `PATCH`, `DELETE` on `/v1/farms/not-a-uuid`.
  - `test_get_accepts_an_uppercase_uuid`: create a farm, `GET` with `farm["id"].upper()` returns `200` and the lowercase `id`.
  - `test_get_accepts_a_uuid_without_hyphens`.
  - `test_existing_hyphenated_row_is_readable_and_deletable`: insert a farm with `test_db.execute` using the seed value `b7e2c0a0-3c1d-4f0a-9a11-0c5d2e6f1001`; `GET` returns it, `DELETE` returns `204`.
  - Update the 503 test to set `DATABASE_URL` instead of patching `db.DB_PATH`.
- [ ] **Step 2: Run** `uv run pytest tests/test_farms.py -q`. Expected: new tests FAIL.
- [ ] **Step 3: Rewrite the queries.** Convert path ids with `parse_uuid`; a `None` result is `404`. Return `Farm(id=str(...), name=...)`. In `delete_farm`, catch `sqlalchemy.exc.IntegrityError`, call `conn.rollback()` and raise the same `409` (Postgres aborts the transaction on a failed statement; the delete is the only write, so rolling back loses nothing).
- [ ] **Step 4: Run** `uv run pytest -q`. Expected: all pass.
- [ ] **Step 5: Commit** "Move farm routes to SQLAlchemy".

---

### Task 6: Plot routes on SQLAlchemy

**Files:** Modify `plots.py`; modify `tests/test_plots.py`.

**Interfaces:**
- Consumes: `db.Conn`, `tables.*`, `ids.parse_uuid`.
- Produces: unchanged routes and models. Helper signatures: `plot_from_row(row) -> Plot` (converts `id` and `farm_id` to `str`), `get_plot_or_404(conn: Connection, plot_id: str) -> Plot`, `check_references(conn: Connection, plot: PlotCreate) -> None` (a malformed or missing `farm_id` raises `422 "Unknown farm"`), `name_taken(conn: Connection, farm_id: UUID, name: str, ignore_id: UUID | None = None) -> bool` (the `id != ignore_id` clause is added only when `ignore_id` is given). `plot_values` is removed: pass `date` objects straight to the query.

- [ ] **Step 1: Add tests** to `tests/test_plots.py`
  - `test_malformed_path_id_returns_404` for `GET`, `PATCH`, `DELETE` on `/v1/plots/garbage`.
  - `test_create_with_a_malformed_farm_id_returns_422_unknown_farm` (detail `"Unknown farm"`, code `VALIDATION`).
  - `test_list_with_a_malformed_farm_id_returns_200_and_empty_list`.
  - `test_list_filter_accepts_an_uppercase_farm_id`.
  - `test_create_first_plot_on_a_farm_works_without_an_ignore_id` (guards the uuid comparison in `name_taken`).
  - `test_patch_moving_a_plot_to_a_farm_with_the_same_name_returns_409`.
  - `test_existing_hyphenated_plot_row_is_patchable`: insert the seed plot row with `test_db.execute` and `PATCH` its name.
  - Update the 503 test to set `DATABASE_URL`; update the race tests (`first_name_taken_misses`, `first_check_passes`) to the new helper signatures; replace any direct `sqlite3` use with `test_db`.
- [ ] **Step 2: Run** `uv run pytest tests/test_plots.py -q`. Expected: new tests FAIL.
- [ ] **Step 3: Rewrite the queries.** Create and update catch `sqlalchemy.exc.IntegrityError`, call `conn.rollback()`, then run the existing recheck (`name_taken`, `check_references`) and re-raise otherwise. Keep every validation rule, message and status code as they are.
- [ ] **Step 4: Run** `uv run pytest -q`. Expected: all pass.
- [ ] **Step 5: Commit** "Move plot routes to SQLAlchemy".

---

### Task 7: Remove the old layer, startup check, perf launcher, README, spec

**Files:** Modify `db.py`, `main.py`, `tests/conftest.py`, `tests/test_db.py`, `tests/test_errors.py`, `perf/run_server.py`, `README.md`, the spec file.

**Interfaces:**
- Produces: `db.py` exports only `ENV_FILE`, `load_env_file`, `get_database_url`, `get_engine`, `reset_engines`, `get_connection`, `Conn`. Rename nothing else.
- `main.py`: `FastAPI(lifespan=lifespan)` where the lifespan calls `db.get_database_url()` on startup (raises `RuntimeError` when missing).

- [ ] **Step 1: Write failing tests**
  - `tests/test_config.py::test_app_refuses_to_start_without_database_url`: `with TestClient(app)` raises `RuntimeError`.
  - `test_app_starts_with_a_database_url_set`.
- [ ] **Step 2: Run** `uv run pytest tests/test_config.py -q`. Expected: first test FAILS.
- [ ] **Step 3: Implement the startup check.** Delete `get_db`, `DB_PATH` and `DbConnection` from `db.py`; delete the `db.DB_PATH` line from the `test_db` fixture; move the remaining `tests/test_db.py` and `tests/test_errors.py` tests onto `db.Conn` / `get_connection` and `DATABASE_URL` (the dependency override test overrides `db.get_connection`). Change `perf/run_server.py` to set `os.environ["DATABASE_URL"] = f"sqlite:///{database}"` (absolute path) instead of `db.DB_PATH`, and update its docstring.
- [ ] **Step 4: Update `README.md`:** database section (two engines, `DATABASE_URL`, `.env.example`, copy to `.env`), the 503 row (a failure to connect, either engine), the running-tests section (`TEST_DATABASE_URL`, the `test` name rule, WSL/Docker note for local Postgres), and the file table (`tables.py`, `ids.py`, `schema.postgres.sql`, `.env.example`). Record that tables must be created in production by running `schema.postgres.sql` once.
- [ ] **Step 5: Apply the four spec amendments** from the top of this plan to the spec file.
- [ ] **Step 6: Run** `uv run pytest -q` and the app by hand: `cp .env.example .env && uv run uvicorn main:app` then `curl localhost:8000/v1/crops`; remove nothing else. Expected: tests pass; the curl returns the two crops (after `bash seed_registry.sh`).
- [ ] **Step 7: Run the performance check** per the README commands (k6 setup unchanged) and report the new p95 next to the old one in `perf/results/`. A p95 above 100 ms is a stop-and-report, not something to tune around.
- [ ] **Step 8: Commit** "Remove the sqlite3 layer and document the two databases".

---

## Self-review notes

- Spec coverage: components, behavior table, edge cases, testing and out-of-scope items each map to a task above. Postgres p95 stays a follow-up, as the spec says.
- Verification limit: no Postgres exists on this machine yet. After Task 7 the Postgres path is verified only by the 503 and parity tests; the `postgres` fixture variants stay skipped. Say so in the final report.
