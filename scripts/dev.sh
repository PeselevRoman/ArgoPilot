#!/usr/bin/env bash
# Start the whole app for development: registry (8000), weather (8001), planner (8002) and the
# frontend (3000). Ctrl+C stops all four.
#
#   scripts/dev.sh           start everything
#   scripts/dev.sh --check   only check that everything could start (files, ports), then exit
#
# Logs go to scripts/.logs/<name>.log. The ports are the ones in each service's .env.example, and
# the planner's .env points at 8000 and 8001, so they are not changeable here (DEV_PORTS exists
# only so the tests can check the port test).

set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib.sh
. "$ROOT/scripts/lib.sh"
load_user_env

PORTS="${DEV_PORTS:-8000 8001 8002 3000}"
PIDS=()

# Check everything that would stop the start, and report all of it at once.
check_prerequisites() {
  local problems=0 service port
  for service in registry-service weather-service planner-service; do
    if [ ! -d "$ROOT/services/$service/.venv" ]; then
      echo "Missing: services/$service/.venv. Run: (cd services/$service && uv sync)"
      problems=1
    fi
    if [ ! -f "$ROOT/services/$service/.env" ]; then
      echo "Missing: services/$service/.env. Run: cp services/$service/.env.example services/$service/.env"
      problems=1
    fi
  done
  if [ ! -d "$ROOT/services/frontend/node_modules" ]; then
    echo "Missing: services/frontend/node_modules. Run: (cd services/frontend && npm install)"
    problems=1
  fi
  if [ ! -f "$ROOT/services/frontend/.env.local" ]; then
    echo "Missing: services/frontend/.env.local. Run: cp services/frontend/.env.example services/frontend/.env.local"
    problems=1
  fi
  for port in $PORTS; do
    if port_in_use "$port"; then
      echo "Port $port is already in use. Stop whatever listens on it, then run this again."
      problems=1
    fi
  done
  return "$problems"
}

# Start one process in its own process group, so that stopping it also stops what it started
# (uv starts python, npm starts node).
start() {
  local name="$1" dir="$2"
  shift 2
  mkdir -p "$LOG_DIR"
  (cd "$ROOT/$dir" && exec setsid "$@") >"$LOG_DIR/$name.log" 2>&1 &
  PIDS+=("$!")
}

STOPPING=0
stop_all() {
  [ "$STOPPING" -eq 0 ] || return 0
  STOPPING=1
  echo
  echo "Stopping..."
  local pid
  for pid in "${PIDS[@]}"; do
    kill -TERM -- "-$pid" 2>/dev/null
  done
  wait 2>/dev/null
}

if ! check_prerequisites; then
  exit 1
fi
if [ "${1:-}" = "--check" ]; then
  echo "Everything is ready: ports $PORTS are free and the files exist."
  exit 0
fi

trap 'stop_all; exit 130' INT TERM
trap stop_all EXIT

start registry services/registry-service uv run uvicorn main:app --host 127.0.0.1 --port 8000
start weather services/weather-service uv run uvicorn main:app --host 127.0.0.1 --port 8001
start planner services/planner-service uv run uvicorn main:app --host 127.0.0.1 --port 8002
start frontend services/frontend npm run dev

# Each service must answer /health before we say it is running. The frontend's first page is
# compiled on the first request, so it gets more time.
wait_or_stop() {
  local name="$1" url="$2" seconds="$3"
  echo -n "Waiting for $name... "
  if wait_for_http "$url" "$seconds"; then
    echo "up"
  else
    echo "did not answer within ${seconds}s. Last lines of $LOG_DIR/$name.log:"
    tail -n 8 "$LOG_DIR/$name.log" | sed 's/^/    /'
    exit 1
  fi
}
wait_or_stop registry http://127.0.0.1:8000/health 60
wait_or_stop weather http://127.0.0.1:8001/health 60
wait_or_stop planner http://127.0.0.1:8002/health 60
wait_or_stop frontend http://127.0.0.1:3000/ 120

echo
echo "Everything is running. Open http://localhost:3000"
echo "Logs: $LOG_DIR/   Press Ctrl+C to stop all four."

# Stay until one of the four exits by itself (or Ctrl+C), then stop the rest.
wait -n
echo "One of the processes exited. See the logs in $LOG_DIR/"
exit 1
