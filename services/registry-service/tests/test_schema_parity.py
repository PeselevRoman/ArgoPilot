import re
from pathlib import Path

SERVICE_DIR = Path(__file__).parent.parent
CONSTRAINT_WORDS = ("UNIQUE", "PRIMARY", "FOREIGN", "CONSTRAINT")
TABLE_PATTERN = re.compile(r"CREATE TABLE\s+(\w+)\s*\((.*?)\n\);", re.DOTALL | re.IGNORECASE)


def parse_tables(path: Path) -> dict[str, list[str]]:
    # Returns {table: [column names in order]}, skipping constraint lines.
    text = path.read_text()
    tables = {}
    for name, body in TABLE_PATTERN.findall(text):
        columns = []
        for line in body.splitlines():
            line = line.strip()
            if not line or line.upper().startswith(CONSTRAINT_WORDS):
                continue
            columns.append(line.split()[0])
        tables[name] = columns
    return tables


def test_both_schema_files_have_the_same_tables_and_columns():
    sqlite_tables = parse_tables(SERVICE_DIR / "schema.sql")
    postgres_tables = parse_tables(SERVICE_DIR / "schema.postgres.sql")

    assert sqlite_tables, "schema.sql has no tables"
    for name in sorted(set(sqlite_tables) | set(postgres_tables)):
        assert sqlite_tables.get(name) == postgres_tables.get(name), (
            f"Table '{name}' differs: schema.sql has {sqlite_tables.get(name)}, "
            f"schema.postgres.sql has {postgres_tables.get(name)}"
        )
    assert sqlite_tables == postgres_tables


def test_postgres_schema_uses_the_native_types():
    text = (SERVICE_DIR / "schema.postgres.sql").read_text()

    assert "uuid" in text
    assert "date" in text
    assert "double precision" in text
    assert 'COLLATE "C"' in text
