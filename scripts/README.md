# scripts

Small helpers for working on the whole project. They are not part of any service.

| File | What it does |
| --- | --- |
| `dev.sh` | Starts the registry (8000), weather (8001), planner (8002) and frontend (3000), waits until each answers, and stops all four on Ctrl+C. `dev.sh --check` only checks that the start would work (files and free ports). |
| `demo.sh` | Starts the stand-in services (`demo/stubs.mjs`) and a second frontend on port 3100 that talks to them, for the P2 presentation. It builds the frontend first (`--no-build` skips that), waits until both answer, and stops both on Ctrl+C. The demo frontend is a production build, because Next.js allows only one `next dev` per folder and `dev.sh` already runs one. `demo.sh --check` only checks the files and ports. |
| `check.sh` | Runs every automated check: the registry, weather and planner tests, the frontend tests, lint, types and build, and the scripts' own tests. One line per suite. `--no-build` skips the frontend build. |
| `lib.sh` | Functions shared by the scripts: finding free ports, waiting for a URL, starting and stopping processes, running suites. It is sourced, never run. |
| `tests/` | Tests for `lib.sh` and for the checks of `dev.sh` and `demo.sh`. |
| `demo/stubs.mjs` | Stand-in registry, weather and planner with canned answers and a control API (`curl localhost:8199/state/<water\|full\|stale\|weather-down\|registry-down\|reset>`), for the P2 presentation. Not the real services. `demo/stubs.test.mjs` tests it (`node --test scripts/demo/stubs.test.mjs`). |

Logs and full test output go to `scripts/.logs/` (not committed).

## PostgreSQL tests

`check.sh` also runs the registry's PostgreSQL tests when `TEST_DATABASE_URL` is set. They drop the tables of that database, so the script refuses any database whose name does not contain `test` (for example `registry_test`). Put the URL in your shell, or in `~/.agropilot-env` outside the repository (the scripts read it and never print it):

```bash
TEST_DATABASE_URL=postgresql://YOUR_ROLE:YOUR_PASSWORD@127.0.0.1:5432/registry_test
```

## Tests of the scripts

From the repository root: `services/registry-service/.venv/bin/python -m pytest scripts/tests`.
