# Shared helpers for scripts/dev.sh and scripts/check.sh. This file is sourced, never run.

# Settings that must not be committed (the PostgreSQL URLs) can live in a file outside the repo.
# It is sourced if it exists, and its contents are never printed.
load_user_env() {
  local file="${AGROPILOT_ENV_FILE:-$HOME/.agropilot-env}"
  if [ -f "$file" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$file"
    set +a
  fi
}

# True (exit 0) when something already listens on 127.0.0.1:$1. It opens a TCP connection with
# bash's /dev/tcp, so it needs no extra tool.
port_in_use() {
  (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null
}

# Wait up to $2 seconds for $1 to answer with a success status.
wait_for_http() {
  local url="$1" seconds="$2" deadline
  deadline=$((SECONDS + seconds))
  while [ "$SECONDS" -lt "$deadline" ]; do
    if curl -fsS -o /dev/null --max-time 2 "$url" 2>/dev/null; then
      return 0
    fi
    sleep 0.5
  done
  return 1
}

# The database name of a URL: the last path segment, without the query string. The user name and
# the query are not part of it, so "test" in either does not count.
db_name_of() {
  local url="${1%%\?*}"
  echo "${url##*/}"
}

# The registry tests drop the five tables of whatever database they are given. Refuse any
# database whose name does not contain "test". The URL (it holds a password) is never printed.
require_test_db() {
  local name
  name="$(db_name_of "$1")"
  case "$name" in
    *test*) return 0 ;;
  esac
  echo "Refusing TEST_DATABASE_URL: the database name must contain 'test' (for example registry_test), because the tests drop its tables." >&2
  return 1
}

# --- running test suites and summarising them -------------------------------------------------

LOG_DIR="${LOG_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.logs}"
SUITE_NAMES=()
SUITE_RESULTS=()
SUITE_NOTES=()

# run_suite NAME DIR COMMAND...: run COMMAND in DIR, keep its output in $LOG_DIR/check-NAME.log
# and remember the result. A failing suite does not stop the next one.
run_suite() {
  local name="$1" dir="$2" log note result
  shift 2
  mkdir -p "$LOG_DIR"
  log="$LOG_DIR/check-$name.log"
  if (cd "$dir" && "$@") >"$log" 2>&1; then
    result=PASS
  else
    result=FAIL
  fi
  # The line that says how it went: pytest's "N passed", vitest's "Tests N passed". A suite that
  # prints no such line (lint, tsc, build) says "ok" when it passed and its last line when it failed.
  note="$(grep -E "[0-9]+ (passed|failed)|Tests +[0-9]" "$log" | tail -1 | sed 's/\x1b\[[0-9;]*m//g' | sed 's/^ *//')"
  if [ -z "$note" ]; then
    if [ "$result" = PASS ]; then
      note=ok
    else
      note="$(tail -1 "$log" | sed 's/\x1b\[[0-9;]*m//g')"
    fi
  fi
  SUITE_NAMES+=("$name")
  SUITE_RESULTS+=("$result")
  SUITE_NOTES+=("$note")
}

# Print one line per suite. Exit status 1 if any suite failed.
print_summary() {
  local i failed=0
  echo
  for i in "${!SUITE_NAMES[@]}"; do
    printf '%-5s %-16s %s\n' "${SUITE_RESULTS[$i]}" "${SUITE_NAMES[$i]}" "${SUITE_NOTES[$i]}"
    [ "${SUITE_RESULTS[$i]}" = PASS ] || failed=1
  done
  if [ "$failed" -eq 1 ]; then
    echo
    echo "Some suites failed. The full output is in $LOG_DIR/check-<name>.log"
    return 1
  fi
  return 0
}
