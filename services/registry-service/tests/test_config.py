from pathlib import Path

import pytest

import config
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


def use_env_file(monkeypatch, tmp_path, content: str) -> None:
    # Point the settings at a temporary .env, like swapping a config asset in a Unity test.
    env_file = tmp_path / ".env"
    env_file.write_text(content)
    monkeypatch.setattr(config, "ENV_FILE", env_file)
    config.get_settings.cache_clear()


def test_env_file_is_read(tmp_path, monkeypatch):
    use_env_file(monkeypatch, tmp_path, "DATABASE_URL=sqlite:///x.db\n")

    assert config.get_settings().database_url == "sqlite:///x.db"


def test_env_variable_wins_over_env_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///from_env.db")
    use_env_file(monkeypatch, tmp_path, "DATABASE_URL=sqlite:///from_file.db\n")

    assert config.get_settings().database_url == "sqlite:///from_env.db"


def test_unrelated_variables_in_env_file_are_ignored(tmp_path, monkeypatch):
    use_env_file(
        monkeypatch, tmp_path,
        "DATABASE_URL=sqlite:///x.db\nWEATHER_URL=http://127.0.0.1:8001\n",
    )

    assert config.get_settings().database_url == "sqlite:///x.db"


def test_database_url_is_stripped(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "  sqlite:///x.db  ")

    assert config.get_settings().database_url == "sqlite:///x.db"


def test_error_message_names_the_variable():
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        config.get_settings()


def test_plain_postgresql_url_uses_the_psycopg_driver(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/t")

    assert db.get_engine().dialect.driver == "psycopg"


def test_relative_sqlite_path_resolves_from_the_service_folder(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///registry.db")

    assert db.get_engine().url.database == str(Path(db.__file__).parent / "registry.db")


def test_app_refuses_to_start_without_database_url():
    from fastapi.testclient import TestClient

    from main import app

    # Entering the client runs the lifespan startup, like Unity's Awake().
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        with TestClient(app):
            pass


def test_app_starts_with_a_database_url_set(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    from main import app

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'x.db'}")

    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
