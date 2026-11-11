from pathlib import Path

import pytest

import db


def test_missing_database_url_raises():
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        db.get_database_url()


def test_empty_database_url_raises(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        db.get_database_url()


def test_unsupported_scheme_raises(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "mysql://x")

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        db.get_database_url()


def test_env_file_is_read(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("DATABASE_URL=sqlite:///x.db\n")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    db.load_env_file(env_file)

    assert db.get_database_url() == "sqlite:///x.db"


def test_env_variable_wins_over_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("DATABASE_URL=sqlite:///from_file.db\n")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///from_env.db")

    db.load_env_file(env_file)

    assert db.get_database_url() == "sqlite:///from_env.db"


def test_plain_postgresql_url_uses_the_psycopg_driver(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/t")

    assert db.get_engine().dialect.driver == "psycopg"


def test_relative_sqlite_path_resolves_from_the_service_folder(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///registry.db")

    assert db.get_engine().url.database == str(Path(db.__file__).parent / "registry.db")
