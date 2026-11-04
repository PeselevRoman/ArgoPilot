import subprocess
from pathlib import Path

import pytest

import db

SEED_SCRIPT = Path(__file__).parent / "seed_test_db.sh"


@pytest.fixture
def test_db(monkeypatch, tmp_path):
    # Each test gets its own fresh catalogue-only database in a temporary folder.
    database = tmp_path / "test.db"
    subprocess.run(["bash", str(SEED_SCRIPT), str(database)], check=True)
    monkeypatch.setattr(db, "DB_PATH", database)
    return database
