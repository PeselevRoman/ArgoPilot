import sqlite3
import subprocess
from pathlib import Path

TESTS_DIR = Path(__file__).parent
REPO_ROOT = TESTS_DIR.parents[2]
COURSE_SEED = REPO_ROOT / "tasks" / "seed_registry.sh"
TEST_SEED = TESTS_DIR / "seed_test_db.sh"


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


def test_course_seed_and_schema_sql_define_the_same_tables(tmp_path):
    course_db = tmp_path / "course.db"
    test_db = tmp_path / "test.db"
    subprocess.run(["bash", str(COURSE_SEED), str(course_db)], check=True, capture_output=True)
    subprocess.run(["bash", str(TEST_SEED), str(test_db)], check=True, capture_output=True)

    course = describe_tables(course_db)
    test = describe_tables(test_db)

    for name in sorted(set(course) | set(test)):
        assert course.get(name) == test.get(name), (
            f"Table '{name}' differs between tasks/seed_registry.sh and schema.sql. "
            "Update both so they match."
        )
