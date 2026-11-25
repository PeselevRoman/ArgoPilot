# Registry P2 Gaps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The registry is set up from nothing with one command on SQLite or PostgreSQL, reads its settings through pydantic-settings, and has its p95 measured on PostgreSQL.

**Architecture:** `config.py` owns settings (`Settings`, `get_settings()`); `db.py` keeps its public functions and delegates to it. `seed.py` creates the schema and loads the 15 rows through the existing `tables.py` Core tables. The two `perf/` scripts accept a database URL as well as a SQLite path, share the schema and catalogue data with `seed.py`, and refuse to rebuild a PostgreSQL database whose name lacks `perf`.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x Core, `psycopg[binary]`, `pydantic-settings` (new, replaces `python-dotenv`), pytest, uv, k6.

**Spec:** `docs/superpowers/specs/2026-11-15-registry-p2-postgres-gaps-design.md`. It builds on `docs/superpowers/specs/2026-11-11-postgres-support-design.md`. Read `docs/judgment-log-p2.md` first, then `docs/judgment-log.md` (section "PostgreSQL support"). Record decisions only in `docs/judgment-log-p2.md`, and only after the learner confirms wording: stop, propose the entry, wait.

## Global Constraints

- Work in `services/registry-service` unless a task says otherwise. Run tests with `uv run pytest -q`. Postgres variants run when `TEST_DATABASE_URL` is set (the learner has `registry_test` on 127.0.0.1:5432); run the suite both ways when a task says so.
- NEVER read any `.env` file (CLAUDE.md rule 11). `services/registry-service/.env` exists and holds the learner's real values. Code reads it; you do not.
- Build only what the design lists: no new routes, no API changes, no Alembic, no `--reset` flag. `seed_registry.sh` and `tests/seed_test_db.sh` are unchanged.
- The seed data is exactly the data in `seed_registry.sh`: 2 farms, 4 plots, 2 crops, 3 soils, 4 emitters (15 rows).
- Never print a database URL with its password. Use `sqlalchemy.engine.make_url(url).render_as_string(hide_password=True)`.
- Every code change has tests. Explain each new file to the learner when it is created (CLAUDE.md rule 10).
- Every commit message ends with the line `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Work is on branch `p2`. Never push.

## Review Focus

Most likely to bite, each pinned by a test in the owning task:

1. A real `.env` leaking into tests: settings read the file on each call, so a developer's `.env` could make "missing `DATABASE_URL`" tests pass or fail wrongly. (Task 2)
2. Extra variables in `.env` (weather and planner add many later, and the learner may already have extras) must not crash startup: pydantic-settings forbids extras from a dotenv file by default. (Task 2)
3. `seed.py` against a database with only some of the tables, or failing halfway, must not leave a half-built database or change existing rows. (Task 3)
4. Pointing the perf seed at a PostgreSQL database whose name lacks `perf` (for example `registry`) must refuse before dropping anything. This is the one data-destroying path. (Task 4)
5. The perf scripts must never print the database password. (Task 4)

---

### Task 1: Block the agent from reading `.env`

**Files:**
- Create: `/home/Roman/ArgoPilot/.claude/settings.json`

- [ ] **Step 1: Create the file** with exactly `{ "permissions": { "deny": ["Read(**/.env)"] } }` (pretty-printed JSON is fine). Check `git check-ignore .claude/settings.json` prints nothing, so it can be committed (`.gitignore` ignores only `.claude/worktrees/`).
- [ ] **Step 2: Verify** the JSON parses: `python3 -m json.tool /home/Roman/ArgoPilot/.claude/settings.json` prints it back. No pytest test: this is a settings file, not code.
- [ ] **Step 3: Commit** `.claude/settings.json` with message "Deny reading .env files to the coding agent".

---

### Task 2: `config.py` with pydantic-settings

**Files:**
- Create: `config.py`
- Modify: `db.py` (remove python-dotenv use), `pyproject.toml` (via uv), `.env.example`, `tests/conftest.py`, `tests/test_config.py`, `README.md` (the "Configuration" text and Layout table)

**Interfaces:**
- Produces:
  - `config.ENV_FILE: Path` — absolute path of the service folder's `.env`. Read at call time, so tests can replace it.
  - `config.Settings(BaseSettings)` with one required field `database_url: str`, `extra="ignore"`.
  - `config.get_settings() -> Settings` — cached with `functools.lru_cache`. Reads `ENV_FILE`; an environment variable wins over the file. Raises `RuntimeError` whose message contains `DATABASE_URL` when the value is missing, blank, or does not start with `sqlite:`, `postgresql:`, `postgres:` (a `+driver` suffix is allowed, as today). The value is stripped.
- Consumes/keeps: `db.get_database_url() -> str` stays and returns `config.get_settings().database_url`. `main.py` is unchanged. `db.load_env_file`, `db.ENV_FILE` and the python-dotenv import are removed.

- [ ] **Step 1: Rewrite `tests/test_config.py`.** Keep these existing tests as they are (they call `db.get_database_url()` or the app): missing, empty, unsupported scheme, plain postgresql URL uses psycopg, relative SQLite path resolves from the service folder, the two app-startup tests. Replace the two `.env` tests with ones that point settings at a temp file:
  - `test_env_file_is_read`: `monkeypatch.setattr(config, "ENV_FILE", tmp_env)`, file contains `DATABASE_URL=sqlite:///x.db`, no env var, `config.get_settings.cache_clear()`, then `config.get_settings().database_url == "sqlite:///x.db"`.
  - `test_env_variable_wins_over_env_file`: file says `from_file.db`, env var says `from_env.db`, result is `sqlite:///from_env.db`.
  - `test_unrelated_variables_in_env_file_are_ignored`: file contains `DATABASE_URL=sqlite:///x.db` and `WEATHER_URL=http://127.0.0.1:8001`; `get_settings()` succeeds.
  - `test_database_url_is_stripped`: env var `"  sqlite:///x.db  "` gives `sqlite:///x.db`.
  - `test_error_message_names_the_variable`: missing value raises `RuntimeError` matching `DATABASE_URL`.
- [ ] **Step 2: Update `tests/conftest.py`** so tests are isolated from the real `.env`. Extend the autouse `clean_database_settings` fixture: add `tmp_path` and `monkeypatch.setattr(config, "ENV_FILE", tmp_path / "no.env")` (a path that does not exist), call `config.get_settings.cache_clear()` before the test and again after it (next to `db.reset_engines()`). Also clear the settings cache in the `test_db` fixture right after it sets `DATABASE_URL`, because the cache may hold an earlier value.
- [ ] **Step 3: Run `uv run pytest -q tests/test_config.py`.** Expected: FAIL (`config` does not exist).
- [ ] **Step 4: Dependencies.** `uv add pydantic-settings` and `uv remove python-dotenv`.
- [ ] **Step 5: Implement `config.py`** as in Interfaces. Build the `Settings` with `Settings(_env_file=ENV_FILE)` inside `get_settings` so the module variable is read at call time. Add a `field_validator("database_url")` that strips and checks the scheme. Catch pydantic's `ValidationError` in `get_settings` and re-raise `RuntimeError("DATABASE_URL is missing or invalid. See .env.example.")` (add the detail text of the validation message after it). Comment each choice for a C# developer (pydantic-settings is like `IOptions<T>` bound to environment variables).
- [ ] **Step 6: Update `db.py`:** `get_database_url()` returns `config.get_settings().database_url`; delete `load_env_file`, `ENV_FILE`, `load_dotenv` and the module-level call. Keep `SERVICE_DIR`, `_normalize`, `get_engine` and the rest unchanged.
- [ ] **Step 7: `.env.example`** keeps `DATABASE_URL=sqlite:///registry.db` and the PostgreSQL form comment (`DATABASE_URL=postgresql://USER:PASSWORD@127.0.0.1:5432/registry`). Use placeholders, never real values.
- [ ] **Step 8: Run the whole suite** `uv run pytest -q`, then `TEST_DATABASE_URL=postgresql://USER:PASSWORD@127.0.0.1:5432/registry_test uv run pytest -q` (the learner supplies the real URL in their shell; ask them to run this second command and paste the result). Expected: all pass; no new skips on the second run.
- [ ] **Step 9: README.** Update the configuration section and the Layout table (`config.py` row, `db.py` row). Explain that a variable already in the environment wins over `.env`.
- [ ] **Step 10: Commit** `config.py`, `db.py`, `pyproject.toml`, `uv.lock`, `.env.example`, tests, README: "Read settings with pydantic-settings in config.py".

---

### Task 3: `seed.py`, the one-command setup (FR-2.2)

**Files:**
- Create: `seed.py`, `tests/test_seed.py`
- Modify: `tests/conftest.py` (new `empty_db` fixture), `README.md`

**Interfaces:**
- Consumes: `db.get_engine() -> Engine`, `tables.farms/plots/crops/soils/emitters` and `tables.metadata`, `schema.sql`, `schema.postgres.sql`.
- Produces in `seed.py`:
  - `CROPS`, `SOILS`, `EMITTERS`, `FARMS`, `PLOTS`: lists of dicts, column name to value, matching `seed_registry.sh`. Ids of farms and plots are `uuid.UUID`, `planting_date` is `datetime.date`.
  - `create_schema(engine: Engine) -> None` — runs `schema.sql` for SQLite and `schema.postgres.sql` otherwise. Splitting the file on `;` is acceptable (the existing `conftest._run_sql_file` does it).
  - `class SeedError(RuntimeError)`.
  - `seed(engine: Engine) -> None` — raises `SeedError` if any of the five tables already exists (check with `sqlalchemy.inspect`), before changing anything. Otherwise creates the schema and inserts all rows in one transaction.
  - `main() -> int` — uses `db.get_engine()`, prints one summary line (database name and row counts, no password), prints the `SeedError` message to stderr and returns 1. Run as `uv run python seed.py`.
- Produces in `conftest.py`: fixture `empty_db`, params `sqlite` and `postgres`, yielding a `TestDatabase` with no tables. SQLite: a temp file URL. PostgreSQL: skipped without `TEST_DATABASE_URL`, refuses names without `test`, drops the five tables. Factor the name guard out of `test_db` into one shared helper rather than copying it.

- [ ] **Step 1: Write the failing tests in `tests/test_seed.py`** (all use `empty_db`, so each runs on both engines):
  - `test_seed_loads_the_fifteen_rows`: after `seed.seed(empty_db.engine)`, counts are farms 2, plots 4, crops 2, soils 3, emitters 4.
  - `test_seed_data_matches_seed_registry_sh` (SQLite only): build one SQLite file with `bash seed_registry.sh <file>` and another with `seed.seed`, then compare every table's rows ordered by `id`, using `sqlite3` from the standard library. Mind the ids: the shell script stores hyphenated text, which is what `UuidId` writes on SQLite.
  - `test_seed_refuses_when_tables_exist`: run twice; the second raises `SeedError` and the row counts are unchanged.
  - `test_seed_refuses_when_only_one_table_exists`: create just `crops` (via `CREATE TABLE crops (id text primary key, name text)`), insert one row, call `seed`; raises `SeedError`, and `crops` still has exactly that row and no other table was created.
  - `test_failed_seed_leaves_nothing`: patch `seed.PLOTS` to hold a plot with an unknown `farm_id`; `seed` raises (`IntegrityError`), and afterwards no tables exist.
  - `test_main_returns_1_when_tables_exist`: with `DATABASE_URL` set (`monkeypatch`) to the empty DB's URL, call `seed.main()` twice: the first returns 0, the second returns 1 and `capsys` stderr is non-empty.
  - `test_main_does_not_print_the_database_url`: `capsys` output of a successful `seed.main()` does not contain the full `DATABASE_URL` string (on SQLite, the file path).
- [ ] **Step 2: Run `uv run pytest -q tests/test_seed.py`.** Expected: FAIL (`seed` does not exist).
- [ ] **Step 3: Implement `seed.py`** as in Interfaces. Explain to the learner why the existence check happens before any write.
- [ ] **Step 4: Run `uv run pytest -q tests/test_seed.py`** and then with `TEST_DATABASE_URL` set (ask the learner to run it). Expected: all pass, none skipped on the second run.
- [ ] **Step 5: Run the real command.** Ask the learner to confirm their own `.env` has the PostgreSQL `registry` URL, then run `uv run python seed.py` from the service folder. Expected: a summary line naming `registry` and 15 rows. Run it again: expected exit code 1 and a refusal message. Verify counts without reading `.env`: `uv run python -c "import db, sqlalchemy as sa; c=db.get_engine().connect(); print([c.execute(sa.text(f'select count(*) from {t}')).scalar() for t in ('farms','plots','crops','soils','emitters')])"` prints `[2, 4, 2, 3, 4]`. If `registry` already has tables from earlier experiments, stop and ask the learner before changing anything.
- [ ] **Step 6: README.** Add a "Set up a new database" section: the exact PostgreSQL steps (create the role and database with `createdb`, set `DATABASE_URL`, run `uv run python seed.py`), the SQLite equivalent, and the refusal behavior. Add `seed.py` to the Layout table and keep `seed_registry.sh`'s row.
- [ ] **Step 7: Decisions.** "Refuse a non-empty database" is already in the log. If you made another decision that a later reader would question, propose an entry and wait for the learner; otherwise write nothing.
- [ ] **Step 8: Commit** `seed.py`, tests, README: "Add seed.py, the one-command setup for an empty database".

---

### Task 4: Performance scripts that accept a database URL

**Files:**
- Create: `perf/perf_target.py`, `perf/tests/test_perf_target.py`
- Modify: `perf/seed_perf_db.py`, `perf/run_server.py`, `perf/record_results.py`, `services/registry-service/README.md` (Performance check section)

**Interfaces:**
- Consumes: `seed.CROPS`, `seed.SOILS`, `seed.EMITTERS`, `seed.create_schema(engine)` from `services/registry-service/seed.py` (add the service folder to `sys.path`, as `run_server.py` already does), and `tables`.
- Produces in `perf/perf_target.py`:
  - `to_url(target: str) -> str` — a string containing `://` is returned unchanged; anything else is a SQLite file path and becomes `sqlite:///<absolute path>`.
  - `check_rebuildable(url: str) -> None` — for non-SQLite URLs raises `SystemExit` unless the database name contains `perf`; SQLite URLs always pass.
  - `safe(url: str) -> str` — the URL with the password hidden, for printing.
- `perf/record_results.py` gains `dataset_line(engine_name: str) -> str` returning the existing dataset sentence plus the engine (`sqlite` or `postgresql`), used in the result file. Its CLI takes an optional second argument, the engine name, default `sqlite`.

- [ ] **Step 1: Write the failing tests in `perf/tests/test_perf_target.py`** (run with the service's Python, `services/registry-service/.venv/bin/python -m pytest perf/tests -q` from the repo root; add `perf/` to `sys.path` at the top of the test file):
  - `test_a_path_becomes_an_absolute_sqlite_url`
  - `test_a_url_is_returned_unchanged`
  - `test_postgres_database_without_perf_in_its_name_is_refused`: `postgresql://u:p@h/registry` raises `SystemExit`; so does `registry_test`.
  - `test_postgres_database_with_perf_in_its_name_is_accepted`: `registry_perf` passes.
  - `test_sqlite_is_always_rebuildable`
  - `test_safe_hides_the_password`: result contains no `secret` for `postgresql://u:secret@h/registry_perf`.
  - `test_dataset_line_names_the_engine`: `dataset_line("postgresql")` contains `postgresql` and `10,000 plots`.
- [ ] **Step 2: Run them.** Expected: FAIL (modules missing).
- [ ] **Step 3: Implement `perf/perf_target.py` and `dataset_line`.** Keep each function a few lines.
- [ ] **Step 4: Rework `perf/seed_perf_db.py`:** the argument goes through `to_url`; call `check_rebuildable` first and exit before touching the database. SQLite: delete the file as before. PostgreSQL: drop the five tables (`DROP TABLE IF EXISTS ... CASCADE`), then `seed.create_schema`. Insert with SQLAlchemy Core and the `tables` objects instead of raw `sqlite3`. Keep the random generator, seed 42 and the data shapes, and reuse `seed.CROPS/SOILS/EMITTERS` instead of redefining them. Print the target with `safe()`. Update the usage docstring to say it runs with the service's Python.
- [ ] **Step 5: Rework `perf/run_server.py`:** accept a path or URL via `to_url`; for a SQLite path keep the "database not found" check; set `DATABASE_URL` as before. Never print the URL unmasked.
- [ ] **Step 6: Update `perf/record_results.py`** to use `dataset_line` with the optional engine argument.
- [ ] **Step 7: Run `perf/tests` and the registry suite** (`uv run pytest -q` in the service folder). Expected: all pass. Confirm the SQLite path still works end to end: `services/registry-service/.venv/bin/python perf/seed_perf_db.py perf/perf.db` prints the usual summary.
- [ ] **Step 8: README Performance section.** Show both forms, with the PostgreSQL one reading the URL from a shell variable (`"$PERF_DATABASE_URL"`), and say the PostgreSQL perf database is rebuilt on every run and must have `perf` in its name.
- [ ] **Step 9: Propose the judgment-log entry** "PostgreSQL performance data lives in a separate `registry_perf` database, guarded by name" (wording as in the design's pending list). Wait for the learner's confirmation, then write it to `docs/judgment-log-p2.md`.
- [ ] **Step 10: Commit** the perf changes and the log entry: "Let the performance scripts target PostgreSQL".

---

### Task 5: Measure NFR-2.2 on PostgreSQL

**Files:**
- Create: a new file in `perf/results/` (written by `record_results.py`)
- Modify: `services/registry-service/README.md` (a short results note)

This task runs a measurement. It needs the learner: `registry_perf` must exist, and k6 must be installed.

- [ ] **Step 1: Ask the learner to create the database** with their own role: `sudo -u postgres createdb -O <their role> registry_perf`, and to export `PERF_DATABASE_URL` in their shell. Do not ask for the password in chat.
- [ ] **Step 2: Build and serve.** From the repo root: `services/registry-service/.venv/bin/python perf/seed_perf_db.py "$PERF_DATABASE_URL"`, expected "100 farms, 10,000 plots" and a masked URL. Start `perf/run_server.py "$PERF_DATABASE_URL"` in the background (port 8001), and check `curl -s http://127.0.0.1:8001/health`.
- [ ] **Step 3: Run k6.** `k6 run --summary-export <scratchpad>/summary.json perf/nfr_1_1.js` (about 12 minutes: ten 60-second runs). Then `python3 perf/record_results.py <scratchpad>/summary.json postgresql`. Stop the server.
- [ ] **Step 4: Report faithfully.** State p95 for every route and for `GET /v1/plots` and `GET /v1/plots/{id}` specifically, against the 100 ms limit, next to the latest SQLite result (`perf/results/2026-11-13T165105Z_v0.1.0.md`). If any route is over 100 ms, that is a finding: report it and stop. Do not tune, retry until green, or edit the numbers.
- [ ] **Step 5: README note** with the measured numbers and the result file name.
- [ ] **Step 6: Commit** the result file and README: "Record the PostgreSQL performance run".

---

## Self-Review

- **Spec coverage:** seed script and its tests (Task 3), config (Task 2), perf on PostgreSQL (Tasks 4 and 5), `.claude/settings.json` (Task 1), README documentation of the PostgreSQL steps (Task 3), log entries (Tasks 3 and 4).
- **Names:** `config.get_settings`, `config.ENV_FILE`, `db.get_database_url`, `seed.seed`, `seed.create_schema`, `seed.SeedError`, `perf_target.to_url`, `check_rebuildable`, `safe` and `dataset_line` are used the same way wherever they appear.
- **Not in the plan on purpose:** a second `.env` loader, a `--reset` flag, and a performance test inside the registry suite.
