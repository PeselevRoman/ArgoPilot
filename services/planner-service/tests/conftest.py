import pytest

import config

SETTING_VARIABLES = (
    "REGISTRY_URL",
    "WEATHER_URL",
    "REGISTRY_TIMEOUT_SECONDS",
    "WEATHER_TIMEOUT_SECONDS",
)


@pytest.fixture(autouse=True)
def clean_settings(monkeypatch, tmp_path):
    # A developer's real .env or shell variables must never leak into a test.
    for name in SETTING_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(config, "ENV_FILE", tmp_path / "no.env")  # a file that does not exist
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


@pytest.fixture
def anyio_backend():
    return "asyncio"


def make_settings(**overrides) -> config.Settings:
    # Explicit values and no .env file, so a test controls every setting.
    values = dict(
        registry_url="http://registry.test",
        weather_url="http://weather.test",
        registry_timeout_seconds=2,
        weather_timeout_seconds=5,
    )
    values.update(overrides)
    return config.Settings(_env_file=None, **values)
