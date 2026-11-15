# Registry service

A web API for managing farms, plots, and the crop, soil, and emitter catalogues used by plots. It is built with FastAPI and runs on SQLite (one file, `registry.db`) or PostgreSQL. `DATABASE_URL` chooses which.

## Requirements

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/) for dependencies
- The `sqlite3` command-line tool, used by the seed script and the test database script
- Optional: a PostgreSQL server, to run on PostgreSQL

## Setup

From this folder:

```bash
uv sync                       # install dependencies from uv.lock
bash seed_registry.sh         # create registry.db with the sample data
cp .env.example .env          # sets DATABASE_URL=sqlite:///registry.db
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

`seed_registry.sh` deletes and rewrites `registry.db` each time it runs. Run it again to get back to the sample data. The database file is not committed to git.

## Database

The service reads `DATABASE_URL` and has no default: without it the server refuses to start. Set it in the environment, or copy `.env.example` to `.env` (not committed). A variable already set in the environment wins over `.env`. Settings are read in `config.py` with pydantic-settings; other variables in `.env` (later services add more) are ignored, and a missing or invalid `DATABASE_URL` stops the start with a clear error.

| Engine | `DATABASE_URL` |
| --- | --- |
| SQLite | `sqlite:///registry.db`. A relative path is resolved from the service folder, not the working directory. |
| PostgreSQL | `postgresql://user:password@host:5432/dbname` |

The service itself never creates tables. To set up a new, empty database, run one command from this folder:

```bash
uv run python seed.py
```

It reads `DATABASE_URL`, creates the tables (`schema.sql` for SQLite, `schema.postgres.sql` for PostgreSQL) and loads the sample data: 2 farms, 4 plots, 2 crops, 3 soils and 4 emitters, the same rows as `seed_registry.sh`. It never deletes anything: if any of the tables already exists, it stops with a message and changes nothing.

Set up PostgreSQL from nothing:

```bash
sudo -u postgres createdb -O YOUR_ROLE registry        # once, with your own role name
# in .env: DATABASE_URL=postgresql://YOUR_ROLE:YOUR_PASSWORD@127.0.0.1:5432/registry
uv run python seed.py
```

SQLite: set `DATABASE_URL=sqlite:///registry.db` and run `uv run python seed.py` (or `bash seed_registry.sh`, which deletes and rewrites the file each time).

Check that the server is up:

```bash
curl http://127.0.0.1:8000/health    # {"status":"ok"}
```

## Resources

**Farm**

| Field | Type | Rules |
| --- | --- | --- |
| `id` | string (UUID) | Set by the server when the farm is created |
| `name` | string | Required. Leading and trailing spaces are removed. A blank name is refused. |

**Plot**

| Field | Type | Rules |
| --- | --- | --- |
| `id` | string (UUID) | Set by the server when the plot is created |
| `farm_id` | string | Must be an existing farm |
| `name` | string | Required, trimmed, not blank. Unique within its farm; the same name can be used on another farm. |
| `area_m2` | number | Greater than 0 |
| `crop_id` | string | Must be an existing crop |
| `planting_date` | string, `YYYY-MM-DD` | Today or earlier, by the server's local date |
| `soil_id` | string | Must be an existing soil |
| `row_spacing_m` | number | Greater than 0 |
| `emitter_spacing_m` | number | Greater than 0 |
| `emitter_id` | string | Must be an existing emitter |
| `lat` | number | From -90 to 90 |
| `lon` | number | From -180 to 180 |

**Catalogues** are read-only and fixed.

| Crop `id` | Name |
| --- | --- |
| `tomato` | Tomato |
| `bell-pepper` | Bell pepper |

| Soil `id` | Name | `available_water_mm_per_m` |
| --- | --- | --- |
| `sand` | Sand | 83 |
| `loam` | Loam | 175 |
| `clay-loam` | Clay loam | 200 |

| Emitter `id` | Name | `flow_lph` |
| --- | --- | --- |
| `dripnet-pc-0.6` | DripNet PC | 0.6 |
| `dripnet-pc-1.0` | DripNet PC | 1.0 |
| `dripnet-pc-1.6` | DripNet PC | 1.6 |
| `dripnet-pc-2.0` | DripNet PC | 2.0 |

Responses contain only the fields in these tables. Extra fields in a request body are ignored.

## Numbers sent as text

A number can be sent as a string. `"1000"`, `"31.25"`, `"1e3"`, and `"1,234,567.5"` are all accepted and converted. Commas are only accepted as thousands separators in groups of three. Booleans, `"inf"`, `"NaN"`, and underscores such as `"1_000"` are refused.

## Routes

| Method | Path | Success | Notes |
| --- | --- | --- | --- |
| `POST` | `/v1/farms` | `201` | Body: `name` |
| `GET` | `/v1/farms` | `200` | List, sorted by `id` |
| `GET` | `/v1/farms/{id}` | `200` | |
| `PATCH` | `/v1/farms/{id}` | `200` | Only the sent fields change |
| `DELETE` | `/v1/farms/{id}` | `204` | Refused with `409` while the farm has plots |
| `POST` | `/v1/plots` | `201` | Body: all plot fields except `id` |
| `GET` | `/v1/plots` | `200` | List, sorted by `id`. Optional `?farm_id=` filter. |
| `GET` | `/v1/plots/{id}` | `200` | |
| `PATCH` | `/v1/plots/{id}` | `200` | Only the sent fields change. The whole plot is checked after the change, and nothing is saved if it is invalid. |
| `DELETE` | `/v1/plots/{id}` | `204` | |
| `GET` | `/v1/crops` | `200` | List, sorted by `id` |
| `GET` | `/v1/crops/{id}` | `200` | |
| `GET` | `/v1/soils` | `200` | List, sorted by `id` |
| `GET` | `/v1/soils/{id}` | `200` | |
| `GET` | `/v1/emitters` | `200` | List, sorted by `id` |
| `GET` | `/v1/emitters/{id}` | `200` | |

An empty list returns `200` with `[]`. A `?farm_id=` that matches no farm also returns `200` with `[]`.

Example: create a plot.

```bash
curl -X POST http://127.0.0.1:8000/v1/plots \
  -H "Content-Type: application/json" \
  -d '{"farm_id": "<farm id>", "name": "South block", "area_m2": 1000,
       "crop_id": "tomato", "planting_date": "2026-03-01", "soil_id": "loam",
       "row_spacing_m": 1.5, "emitter_spacing_m": 0.4, "emitter_id": "dripnet-pc-1.0",
       "lat": 31.25, "lon": 34.79}'
```

## Errors

Every error response uses `application/problem+json` and has a `code` field.

| Status | `code` | When |
| --- | --- | --- |
| `422` | `VALIDATION` | A field is invalid, or a referenced farm, crop, soil, or emitter does not exist. Also when a `PATCH` would leave the plot invalid. |
| `404` | `NOT_FOUND` | The id in the URL does not exist, or the URL is not a route |
| `409` | `CONFLICT` | A plot name is already used on the same farm, or a farm with plots is deleted |
| `405` | `VALIDATION` | The HTTP method is not allowed on that route. The `Allow` header lists the allowed methods. |
| `503` | `UNAVAILABLE` | The service cannot connect to the database: the SQLite file is missing, or PostgreSQL is unreachable. The response includes `Retry-After: 5`. The cause is logged. |

The `title` in each error follows the standard reason phrase for its status, for example "Unprocessable Content" for `422`.

## Transactions

Each request runs in one transaction. Its changes are saved only if the request succeeds, and the save happens before the response is sent.

## Tests

From this folder:

```bash
uv run pytest
```

The tests build their own temporary databases, so they never change `registry.db`. The test database script `tests/seed_test_db.sh` needs `bash` and `sqlite3`.

Each database test runs on SQLite and, when `TEST_DATABASE_URL` is set, on PostgreSQL too. Without it the `postgres` variants are skipped.

```bash
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/registry_test uv run pytest
```

Set `TEST_DATABASE_URL` in the shell, on the command line or with `export`, not in `.env`: the service reads only the settings it declares in `config.py`, so a `TEST_DATABASE_URL` line in `.env` is ignored and the PostgreSQL tests are skipped without a warning.

The PostgreSQL test database is dropped and rebuilt on every test, so its name must contain `test`; the tests refuse to run otherwise. On Windows, run PostgreSQL inside WSL or in Docker (for example `docker run -e POSTGRES_PASSWORD=pw -p 5432:5432 postgres`) and connect to `localhost`.

## Performance check

The performance check measures the list and get-by-id routes at 10 requests per second each. The target is a 95th-percentile response time under 100 ms. It needs [k6](https://k6.io), which is installed separately from this project.

From the repository root, on SQLite:

```bash
services/registry-service/.venv/bin/python perf/seed_perf_db.py perf/perf.db   # 100 farms, 10,000 plots
services/registry-service/.venv/bin/python perf/run_server.py perf/perf.db &   # server on port 8001
k6 run --summary-export summary.json perf/nfr_1_1.js
python3 perf/record_results.py summary.json                                    # writes perf/results/
```

On PostgreSQL, use a separate database whose name contains `perf` (for example `registry_perf`), and give the scripts its URL from a shell variable:

```bash
export PERF_DATABASE_URL='postgresql://YOUR_ROLE:YOUR_PASSWORD@127.0.0.1:5432/registry_perf'
services/registry-service/.venv/bin/python perf/seed_perf_db.py "$PERF_DATABASE_URL"
services/registry-service/.venv/bin/python perf/run_server.py "$PERF_DATABASE_URL" &
k6 run --summary-export summary.json perf/nfr_1_1.js
python3 perf/record_results.py summary.json postgresql
```

The PostgreSQL perf database is rebuilt on every run: its tables are dropped first. The script refuses any target whose name does not contain `perf` (the database name, or the SQLite file name), so `registry` or `registry.db` cannot be wiped by mistake. A `dbname` or `database` query parameter in the URL is refused too. The scripts print the URL with the password hidden.

The perf helpers have their own small tests: `services/registry-service/.venv/bin/python -m pytest perf/tests`, from the repository root.

The results of each run are kept in `perf/results/`.

Latest runs, p95 at 10 requests per second (limit 100 ms):

| Route | SQLite (2026-11-13) | PostgreSQL (2026-11-15) |
| --- | --- | --- |
| `GET /v1/plots` (list, 10,000 rows) | 86.56 ms | 83.50 ms |
| `GET /v1/plots/{id}` | 6.51 ms | 7.62 ms |

All ten routes passed on PostgreSQL, with 0.00% failed requests. The list of plots is the slowest route on both engines and has about 16% headroom. See `perf/results/2026-11-15T152751Z_v0.1.0.md`.

## Layout

| File | Purpose |
| --- | --- |
| `main.py` | Creates the app and connects the routes and error handling |
| `config.py` | Reads and checks the settings (`DATABASE_URL`) from the environment and `.env` |
| `db.py` | Builds the engine, and gives each request one connection and transaction (`db.Conn`) |
| `tables.py` | The five tables as SQLAlchemy `Table` objects |
| `ids.py` | Parses id text as a UUID |
| `errors.py` | Turns every error into `application/problem+json` |
| `farms.py` | Farm routes |
| `plots.py` | Plot routes and validation |
| `catalogues.py` | Crop, soil, and emitter routes |
| `schema.sql` | SQLite table definitions, used by the seed script and the tests |
| `schema.postgres.sql` | PostgreSQL table definitions, run once by hand in production and by the tests |
| `.env.example` | Example `DATABASE_URL`; copy to `.env` |
| `seed.py` | Creates the tables and loads the sample data in an empty SQLite or PostgreSQL database |
| `seed_registry.sh` | Creates `registry.db` with the sample data (SQLite only) |
| `tests/` | Test suite |

## Design decisions

The reasons for the main choices are in [`docs/judgment-log.md`](../../docs/judgment-log.md).
