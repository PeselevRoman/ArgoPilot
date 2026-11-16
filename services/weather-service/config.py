"""Settings for weather-service, read from the environment and from .env.

pydantic-settings works like IOptions<T> in C#: a typed class is filled from
environment variables (and a .env file), and invalid values fail at startup.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute, so it does not depend on the folder the server starts from.
# Module variable, read at call time, so tests can point it at another file.
ENV_FILE = Path(__file__).parent / ".env"


class Settings(BaseSettings):
    # extra="ignore": other services' variables in the same .env must not crash startup.
    model_config = SettingsConfigDict(extra="ignore")

    provider_base_url: str
    provider_api_key: str = ""  # the only optional setting
    provider_timeout_seconds: float
    provider_retries: int
    provider_retry_delay_seconds: float
    freshness_hours: float
    max_stale_hours: float
    retry_after_seconds: int

    @field_validator("provider_base_url")
    @classmethod
    def check_base_url(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith(("http://", "https://")):
            raise ValueError("PROVIDER_BASE_URL must start with http:// or https://")
        return value

    @field_validator("provider_timeout_seconds")
    @classmethod
    def check_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("PROVIDER_TIMEOUT_SECONDS must be greater than 0")
        return value

    @field_validator("provider_retries")
    @classmethod
    def check_retries(cls, value: int) -> int:
        if value < 0:
            raise ValueError("PROVIDER_RETRIES must be 0 or more")
        return value

    @field_validator("provider_retry_delay_seconds")
    @classmethod
    def check_delay(cls, value: float) -> float:
        if value < 0:
            raise ValueError("PROVIDER_RETRY_DELAY_SECONDS must be 0 or more")
        return value

    @field_validator("freshness_hours")
    @classmethod
    def check_freshness(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("FRESHNESS_HOURS must be greater than 0")
        return value

    @field_validator("retry_after_seconds")
    @classmethod
    def check_retry_after(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("RETRY_AFTER_SECONDS must be greater than 0")
        return value

    @model_validator(mode="after")
    def check_stale_limit(self) -> "Settings":
        if self.max_stale_hours < self.freshness_hours:
            raise ValueError("MAX_STALE_HOURS must not be less than FRESHNESS_HOURS")
        return self


def _describe(item: dict) -> str:
    # Missing and wrongly typed values carry the field name in loc; the custom
    # validators already name their variable in the message.
    name = str(item["loc"][0]).upper() if item["loc"] else ""
    message = item["msg"].removeprefix("Value error, ")
    return message if name in message else f"{name}: {message}"


@lru_cache
def get_settings() -> Settings:
    # Cached, so the .env file is not re-read on every request. Failures are not cached.
    try:
        return Settings(_env_file=ENV_FILE)
    except ValidationError as error:
        detail = "; ".join(_describe(item) for item in error.errors())
        raise RuntimeError(f"Invalid or missing settings. See .env.example. ({detail})") from None
