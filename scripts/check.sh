#!/usr/bin/env bash
# Run every automated check of the project, one after the other, and print one line per suite.
#
#   scripts/check.sh              all suites, including the frontend production build
#   scripts/check.sh --no-build   skip the frontend build (it is the slowest step)
#
# The registry's PostgreSQL tests run too when TEST_DATABASE_URL is set, in your shell or in
# ~/.agropilot-env (outside the repository, never printed). They drop the tables of that
# database, so its name must contain "test", for example registry_test.
# Full output of each suite: scripts/.logs/check-<name>.log

set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib.sh
. "$ROOT/scripts/lib.sh"
load_user_env

if [ -n "${TEST_DATABASE_URL:-}" ]; then
  require_test_db "$TEST_DATABASE_URL" || exit 2
  echo "Registry tests: SQLite and PostgreSQL"
else
  echo "Registry tests: SQLite only (set TEST_DATABASE_URL to a database named like registry_test to include PostgreSQL)"
fi

run_suite registry "$ROOT/services/registry-service" uv run pytest -q
run_suite weather "$ROOT/services/weather-service" uv run pytest -q
run_suite planner "$ROOT/services/planner-service" uv run pytest -q
run_suite frontend-tests "$ROOT/services/frontend" npm test
run_suite frontend-lint "$ROOT/services/frontend" npm run lint
run_suite frontend-types "$ROOT/services/frontend" npx tsc --noEmit
if [ "${1:-}" != "--no-build" ]; then
  run_suite frontend-build "$ROOT/services/frontend" npm run build
fi
# The demo stand-in's tests (Node's own test runner, no extra package).
run_suite demo-stubs "$ROOT" node --test scripts/demo/stubs.test.mjs
# The scripts' own tests, with the registry's Python.
run_suite scripts "$ROOT" "$ROOT/services/registry-service/.venv/bin/python" -m pytest -q scripts/tests

print_summary
