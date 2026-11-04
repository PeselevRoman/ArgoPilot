#!/usr/bin/env bash
# Build a catalogue-only SQLite file for the test suite.
# The table definitions come from ../schema.sql. Only the catalogue rows are
# inserted here. Farms and plots tables exist but stay empty until the steps
# that need them are built.
# Safe to run again: it deletes the file and writes a fresh one.
#
# Usage:
#   bash tests/seed_test_db.sh /path/to/test.db

set -euo pipefail

if ! command -v sqlite3 >/dev/null 2>&1; then
  echo "sqlite3 is not installed." >&2
  exit 1
fi

db="${1:?usage: seed_test_db.sh /path/to/test.db}"
schema="$(dirname "$0")/../schema.sql"
rm -f "$db"

sqlite3 "$db" < "$schema"

sqlite3 "$db" <<'SQL'
INSERT INTO crops (id, name) VALUES
  ('tomato', 'Tomato'),
  ('bell-pepper', 'Bell pepper');

INSERT INTO soils (id, name, available_water_mm_per_m) VALUES
  ('sand', 'Sand', 83),
  ('loam', 'Loam', 175),
  ('clay-loam', 'Clay loam', 200);

INSERT INTO emitters (id, name, flow_lph) VALUES
  ('dripnet-pc-0.6', 'DripNet PC', 0.6),
  ('dripnet-pc-1.0', 'DripNet PC', 1.0),
  ('dripnet-pc-1.6', 'DripNet PC', 1.6),
  ('dripnet-pc-2.0', 'DripNet PC', 2.0);
SQL
