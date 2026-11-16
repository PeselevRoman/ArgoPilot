import pytest

import config

VALID_ENV = {
    "REGISTRY_URL": "http://registry.test",
    "WEATHER_URL": "http://weather.test",
    "REGISTRY_TIMEOUT_SECONDS": "2",
    "WEATHER_TIMEOUT_SECONDS": "5",
}


def set_env(monkeypatch, **overrides):
    values = {**VALID_ENV, **overrides}
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    config.get_settings.cache_clear()


def test_missing_variable_fails_and_names_it():
    with pytest.raises(RuntimeError, match="REGISTRY_URL"):
        config.get_settings()


def test_error_mentions_env_example():
    with pytest.raises(RuntimeError, match=r"\.env\.example"):
        config.get_settings()


def test_env_file_is_read(monkeypatch, tmp_path):
    env_file = tmp_path / "service.env"
    env_file.write_text("\n".join(f"{k}={v}" for k, v in VALID_ENV.items()))
    monkeypatch.setattr(config, "ENV_FILE", env_file)
    config.get_settings.cache_clear()
    settings = config.get_settings()
    assert settings.registry_url == "http://registry.test"
    assert settings.weather_timeout_seconds == 5


def test_environment_wins_over_env_file(monkeypatch, tmp_path):
    env_file = tmp_path / "service.env"
    env_file.write_text("\n".join(f"{k}={v}" for k, v in VALID_ENV.items()))
    monkeypatch.setattr(config, "ENV_FILE", env_file)
    monkeypatch.setenv("REGISTRY_URL", "https://other.test")
    config.get_settings.cache_clear()
    assert config.get_settings().registry_url == "https://other.test"


def test_unrelated_variables_in_env_file_are_ignored(monkeypatch, tmp_path):
    env_file = tmp_path / "service.env"
    lines = [f"{k}={v}" for k, v in VALID_ENV.items()] + ["DATABASE_URL=sqlite:///x.db"]
    env_file.write_text("\n".join(lines))
    monkeypatch.setattr(config, "ENV_FILE", env_file)
    config.get_settings.cache_clear()
    assert config.get_settings().weather_url == "http://weather.test"


@pytest.mark.parametrize(
    "name, value",
    [
        ("REGISTRY_URL", "ftp://registry.test"),
        ("WEATHER_URL", "ftp://weather.test"),
        ("REGISTRY_TIMEOUT_SECONDS", "0"),
        ("WEATHER_TIMEOUT_SECONDS", "0"),
        ("REGISTRY_TIMEOUT_SECONDS", "601"),
        ("WEATHER_TIMEOUT_SECONDS", "601"),
    ],
)
def test_invalid_value_is_refused(monkeypatch, name, value):
    set_env(monkeypatch, **{name: value})
    with pytest.raises(RuntimeError, match=name):
        config.get_settings()


@pytest.mark.parametrize("name", ["REGISTRY_TIMEOUT_SECONDS", "WEATHER_TIMEOUT_SECONDS"])
@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
def test_non_finite_timeout_is_refused(monkeypatch, name, value):
    set_env(monkeypatch, **{name: value})
    with pytest.raises(RuntimeError, match=name):
        config.get_settings()
