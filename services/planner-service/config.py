"""Settings for planner-service, read from the environment and from .env.

pydantic-settings works like IOptions<T> in C#: a typed class is filled from
environment variables (and a .env file), and invalid values fail at startup.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute, so it does not depend on the folder the server starts from.
# Module variable, read at call time, so tests can point it at another file.
ENV_FILE = Path(__file__).parent / ".env"

# Longer timeouts are a typo; no call to another service should wait ten minutes.
MAX_TIMEOUT_SECONDS = 600


class Settings(BaseSettings):
    # extra="ignore": other services' variables in the same .env must not crash startup.
    # allow_inf_nan=False: "nan" or "inf" would pass the "greater than 0" check
    # (every comparison with nan is False) and then break every request later.
    model_config = SettingsConfigDict(extra="ignore", allow_inf_nan=False)

    registry_url: str
    weather_url: str
    registry_timeout_seconds: float
    weather_timeout_seconds: float

    @field_validator("registry_url")
    @classmethod
    def check_registry_url(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith(("http://", "https://")):
            raise ValueError("REGISTRY_URL must start with http:// or https://")
        return value

    @field_validator("weather_url")
    @classmethod
    def check_weather_url(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith(("http://", "https://")):
            raise ValueError("WEATHER_URL must start with http:// or https://")
        return value

    @field_validator("registry_timeout_seconds")
    @classmethod
    def check_registry_timeout(cls, value: float) -> float:
        if value <= 0 or value > MAX_TIMEOUT_SECONDS:
            raise ValueError(
                f"REGISTRY_TIMEOUT_SECONDS must be greater than 0 and at most {MAX_TIMEOUT_SECONDS}"
            )
        return value

    @field_validator("weather_timeout_seconds")
    @classmethod
    def check_weather_timeout(cls, value: float) -> float:
        if value <= 0 or value > MAX_TIMEOUT_SECONDS:
            raise ValueError(
                f"WEATHER_TIMEOUT_SECONDS must be greater than 0 and at most {MAX_TIMEOUT_SECONDS}"
            )
        return value


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
