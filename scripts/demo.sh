#!/usr/bin/env bash
# Start what the P2 demo needs, apart from the real app (scripts/dev.sh): the stand-in services
# (scripts/demo/stubs.mjs, canned answers) and a second frontend on port 3100 that talks to them.
# Ctrl+C stops both.
#
#   scripts/demo.sh             build the frontend, start both, wait until they answer
#   scripts/demo.sh --no-build  skip the build (use it when the frontend code has not changed)
#   scripts/demo.sh --check     only check that it could start (node, files, free ports), then exit
#
# The demo frontend runs as a production build (`next start`), not `next dev`: Next.js allows
# only one `next dev` per folder, and dev.sh already runs one on port 3000.
# Ports: stand-in registry 8100, weather 8101, planner 8102, control 8199; frontend 3100.
# (DEMO_PORTS exists only so the tests can check the port test.)

set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib.sh
. "$ROOT/scripts/lib.sh"

PORTS="${DEMO_PORTS:-8100 8101 8102 8199 3100}"
BUILD=1
CHECK_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --no-build) BUILD=0 ;;
    --check) CHECK_ONLY=1 ;;
    *) echo "Unknown option: $arg (use --no-build or --check)"; exit 2 ;;
  esac
done

check_prerequisites() {
  local problems=0 port
  if ! command -v node >/dev/null 2>&1; then
    echo "Missing: node. Install Node.js 22 or newer."
    problems=1
  fi
  if [ ! -d "$ROOT/services/frontend/node_modules" ]; then
    echo "Missing: services/frontend/node_modules. Run: (cd services/frontend && npm install)"
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

if ! check_prerequisites; then
  exit 1
fi
if [ "$CHECK_ONLY" -eq 1 ]; then
  echo "Everything is ready: ports $PORTS are free and the files exist."
  exit 0
fi

trap 'stop_all; exit 130' INT TERM
trap stop_all EXIT

if [ "$BUILD" -eq 1 ]; then
  echo -n "Building the frontend (about 10 seconds)... "
  mkdir -p "$LOG_DIR"
  if (cd "$ROOT/services/frontend" && npm run build) >"$LOG_DIR/demo-build.log" 2>&1; then
    echo "done"
  else
    echo "failed. Last lines of $LOG_DIR/demo-build.log:"
    tail -n 12 "$LOG_DIR/demo-build.log" | sed 's/^/    /'
    exit 1
  fi
fi

start demo-stubs . node scripts/demo/stubs.mjs
start demo-frontend services/frontend env \
  REGISTRY_URL=http://127.0.0.1:8100 WEATHER_URL=http://127.0.0.1:8101 \
  PLANNER_URL=http://127.0.0.1:8102 REQUEST_TIMEOUT_MS=1500 \
  npx next start -p 3100

wait_or_stop demo-stubs http://127.0.0.1:8199/state 20
wait_or_stop demo-frontend http://127.0.0.1:3100/ 60

echo
echo "The demo is running (the stand-in gives canned answers, not the real services)."
echo "  Plot page:  http://localhost:3100/plots/p1"
echo "  Switch the state with:  curl localhost:8199/state/<water|full|stale|weather-down|registry-down|reset>"
echo "  Logs: $LOG_DIR/   Press Ctrl+C to stop both."

# Stay until one of the two exits by itself (or Ctrl+C), then stop the other.
wait -n
echo "One of the processes exited. See the logs in $LOG_DIR/"
exit 1
