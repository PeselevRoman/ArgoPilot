import pytest

import config

VALID_ENV = {
    "PROVIDER_BASE_URL": "http://provider.test",
    "PROVIDER_TIMEOUT_SECONDS": "2",
    "PROVIDER_RETRIES": "2",
    "PROVIDER_RETRY_DELAY_SECONDS": "0",
    "FRESHNESS_HOURS": "3",
    "MAX_STALE_HOURS": "24",
    "RETRY_AFTER_SECONDS": "60",
}


def set_env(monkeypatch, **overrides):
    values = {**VALID_ENV, **overrides}
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    config.get_settings.cache_clear()


def test_missing_variable_fails_and_names_it():
    with pytest.raises(RuntimeError, match="PROVIDER_BASE_URL"):
        config.get_settings()


def test_error_mentions_env_example():
    with pytest.raises(RuntimeError, match=r"\.env\.example"):
        config.get_settings()


def test_valid_environment_loads(monkeypatch):
    set_env(monkeypatch)
    settings = config.get_settings()
    assert settings.provider_base_url == "http://provider.test"
    assert settings.provider_retries == 2
    assert settings.max_stale_hours == 24


def test_api_key_may_be_empty(monkeypatch):
    set_env(monkeypatch)
    assert config.get_settings().provider_api_key == ""


def test_env_file_is_read(monkeypatch, tmp_path):
    env_file = tmp_path / "service.env"
    env_file.write_text("\n".join(f"{k}={v}" for k, v in VALID_ENV.items()))
    monkeypatch.setattr(config, "ENV_FILE", env_file)
    config.get_settings.cache_clear()
    assert config.get_settings().provider_base_url == "http://provider.test"


def test_environment_wins_over_env_file(monkeypatch, tmp_path):
    env_file = tmp_path / "service.env"
    env_file.write_text("\n".join(f"{k}={v}" for k, v in VALID_ENV.items()))
    monkeypatch.setattr(config, "ENV_FILE", env_file)
    monkeypatch.setenv("PROVIDER_BASE_URL", "https://other.test")
    config.get_settings.cache_clear()
    assert config.get_settings().provider_base_url == "https://other.test"


def test_unrelated_variables_in_env_file_are_ignored(monkeypatch, tmp_path):
    env_file = tmp_path / "service.env"
    lines = [f"{k}={v}" for k, v in VALID_ENV.items()] + ["DATABASE_URL=sqlite:///x.db"]
    env_file.write_text("\n".join(lines))
    monkeypatch.setattr(config, "ENV_FILE", env_file)
    config.get_settings.cache_clear()
    assert config.get_settings().provider_base_url == "http://provider.test"


@pytest.mark.parametrize(
    "name, value",
    [
        ("PROVIDER_BASE_URL", "ftp://provider.test"),
        ("PROVIDER_TIMEOUT_SECONDS", "0"),
        ("PROVIDER_RETRIES", "-1"),
        ("PROVIDER_RETRY_DELAY_SECONDS", "-1"),
        ("FRESHNESS_HOURS", "0"),
        ("MAX_STALE_HOURS", "2"),  # below freshness (3)
        ("RETRY_AFTER_SECONDS", "0"),
    ],
)
def test_invalid_value_is_refused(monkeypatch, name, value):
    set_env(monkeypatch, **{name: value})
    with pytest.raises(RuntimeError, match=name):
        config.get_settings()


@pytest.mark.parametrize("name", [
    "PROVIDER_TIMEOUT_SECONDS", "PROVIDER_RETRY_DELAY_SECONDS", "FRESHNESS_HOURS", "MAX_STALE_HOURS",
])
@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
def test_non_finite_numbers_are_refused_at_startup(monkeypatch, name, value):
    set_env(monkeypatch, **{name: value})
    with pytest.raises(RuntimeError, match=name):
        config.get_settings()


@pytest.mark.parametrize("name", ["FRESHNESS_HOURS", "MAX_STALE_HOURS"])
def test_absurdly_long_periods_are_refused_at_startup(monkeypatch, name):
    # 1e12 hours would overflow date arithmetic and make every request fail later.
    set_env(monkeypatch, **{name: "1e12"})
    with pytest.raises(RuntimeError, match=name):
        config.get_settings()


def test_one_year_is_the_longest_period_accepted(monkeypatch):
    set_env(monkeypatch, FRESHNESS_HOURS="8760", MAX_STALE_HOURS="8760")

    assert config.get_settings().max_stale_hours == 8760
