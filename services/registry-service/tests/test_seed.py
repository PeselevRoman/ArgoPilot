import sqlite3
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import text

import seed

SERVICE_DIR = Path(__file__).parent.parent
TABLES = ("crops", "soils", "emitters", "farms", "plots")


def counts(database) -> dict[str, int]:
    return {t: database.fetch_all(f"SELECT count(*) FROM {t}")[0][0] for t in TABLES}


def existing_tables(database) -> set[str]:
    with database.engine.connect() as conn:
        from sqlalchemy import inspect

        return set(inspect(conn).get_table_names())


def test_seed_loads_the_fifteen_rows(empty_db):
    seed.seed(empty_db.engine)

    assert counts(empty_db) == {"crops": 2, "soils": 3, "emitters": 4, "farms": 2, "plots": 4}


def test_seed_data_matches_seed_registry_sh(tmp_path, monkeypatch):
    from sqlalchemy import create_engine

    from_script = tmp_path / "script.db"
    subprocess.run(["bash", str(SERVICE_DIR / "seed_registry.sh"), str(from_script)], check=True, capture_output=True)
    from_python = tmp_path / "python.db"
    engine = create_engine(f"sqlite:///{from_python}")
    seed.seed(engine)
    engine.dispose()

    def dump(path: Path) -> dict[str, list]:
        conn = sqlite3.connect(path)
        try:
            return {t: conn.execute(f"SELECT * FROM {t} ORDER BY id").fetchall() for t in TABLES}
        finally:
            conn.close()

    assert dump(from_python) == dump(from_script)


def test_seed_refuses_when_tables_exist(empty_db):
    seed.seed(empty_db.engine)

    with pytest.raises(seed.SeedError):
        seed.seed(empty_db.engine)

    assert counts(empty_db) == {"crops": 2, "soils": 3, "emitters": 4, "farms": 2, "plots": 4}


def test_seed_refuses_when_only_one_table_exists(empty_db):
    empty_db.execute("CREATE TABLE crops (id text primary key, name text)")
    empty_db.execute("INSERT INTO crops (id, name) VALUES ('x', 'X')")

    with pytest.raises(seed.SeedError):
        seed.seed(empty_db.engine)

    assert empty_db.fetch_all("SELECT id, name FROM crops") == [("x", "X")]
    assert existing_tables(empty_db) == {"crops"}


def test_failed_seed_leaves_nothing(empty_db, monkeypatch):
    bad_plot = dict(seed.PLOTS[0], farm_id=seed.PLOTS[0]["id"])  # a farm id that does not exist
    monkeypatch.setattr(seed, "PLOTS", [bad_plot])

    with pytest.raises(Exception):
        seed.seed(empty_db.engine)

    assert existing_tables(empty_db) == set()


def test_main_returns_1_when_tables_exist(empty_db, capsys):
    assert seed.main() == 0
    capsys.readouterr()

    assert seed.main() == 1
    assert capsys.readouterr().err != ""


def test_main_does_not_print_the_database_url(empty_db, capsys):
    assert seed.main() == 0

    output = capsys.readouterr()
    assert empty_db.url not in output.out + output.err


def test_main_prints_one_line_when_the_database_is_unreachable(set_database_url, capsys):
    set_database_url("postgresql://u:p@127.0.0.1:1/test")  # nothing listens on port 1

    assert seed.main() == 1

    error = capsys.readouterr().err
    assert "Could not connect" in error
    assert "Traceback" not in error
    assert len(error.strip().splitlines()) == 1
