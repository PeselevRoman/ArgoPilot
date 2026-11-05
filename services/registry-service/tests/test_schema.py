import json
import sqlite3
from pathlib import Path

TESTS_DIR = Path(__file__).parent
SCHEMA_SQL = TESTS_DIR.parent / "schema.sql"
EXPECTED_SCHEMA = TESTS_DIR / "expected_schema.json"


def describe_tables(database: Path) -> dict:
    # Structure only: columns, foreign keys, and unique constraints.
    # Formatting and whitespace in the SQL text do not matter.
    conn = sqlite3.connect(database)
    names = [
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
    ]
    description = {}
    for name in sorted(names):
        columns = [tuple(row[1:6]) for row in conn.execute(f"PRAGMA table_info({name})")]
        foreign_keys = sorted(tuple(row[2:5]) for row in conn.execute(f"PRAGMA foreign_key_list({name})"))
        indexes = []
        for row in conn.execute(f"PRAGMA index_list({name})"):
            index_columns = tuple(info[2] for info in conn.execute(f"PRAGMA index_info({row[1]})"))
            indexes.append((row[2], row[3], index_columns))
        description[name] = {
            "columns": columns,
            "foreign_keys": foreign_keys,
            "indexes": sorted(indexes),
        }
    conn.close()
    return description


def test_schema_sql_matches_the_saved_structure(tmp_path):
    database = tmp_path / "schema.db"
    conn = sqlite3.connect(database)
    conn.executescript(SCHEMA_SQL.read_text())
    conn.close()

    # Round-trip through JSON so tuples compare equal to the saved lists.
    actual = json.loads(json.dumps(describe_tables(database)))
    expected = json.loads(EXPECTED_SCHEMA.read_text())

    for name in sorted(set(actual) | set(expected)):
        assert actual.get(name) == expected.get(name), (
            f"Table '{name}' differs from tests/expected_schema.json. "
            "If the change is intended, update that file to match."
        )
