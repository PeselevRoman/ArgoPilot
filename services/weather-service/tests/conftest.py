import pytest

import config

SETTING_VARIABLES = (
    "PROVIDER_BASE_URL",
    "PROVIDER_API_KEY",
    "PROVIDER_TIMEOUT_SECONDS",
    "PROVIDER_RETRIES",
    "PROVIDER_RETRY_DELAY_SECONDS",
    "FRESHNESS_HOURS",
    "MAX_STALE_HOURS",
    "RETRY_AFTER_SECONDS",
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


def make_settings(**overrides) -> config.Settings:
    # Explicit values and no .env file, so a test controls every setting.
    values = dict(
        provider_base_url="http://provider.test",
        provider_api_key="",
        provider_timeout_seconds=2,
        provider_retries=2,
        provider_retry_delay_seconds=0,
        freshness_hours=3,
        max_stale_hours=24,
        retry_after_seconds=60,
    )
    values.update(overrides)
    return config.Settings(_env_file=None, **values)
