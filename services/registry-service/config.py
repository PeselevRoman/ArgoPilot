"""Settings for registry-service, read from the environment and from .env.

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

SUPPORTED_BACKENDS = ("sqlite", "postgresql", "postgres")


class Settings(BaseSettings):
    # extra="ignore": other services' variables in the same .env must not crash startup.
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str  # no default: a missing value is an error

    @field_validator("database_url")
    @classmethod
    def check_database_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("DATABASE_URL is empty")
        backend = value.split(":", 1)[0].split("+", 1)[0]
        if backend not in SUPPORTED_BACKENDS:
            raise ValueError("DATABASE_URL must start with sqlite: or postgresql:")
        return value


@lru_cache
def get_settings() -> Settings:
    # Cached, because the engine lookup asks for the URL on every request and
    # re-reading the .env file each time would be wasted work. Failures are not cached.
    try:
        return Settings(_env_file=ENV_FILE)
    except ValidationError as error:
        detail = "; ".join(item["msg"] for item in error.errors())
        raise RuntimeError(f"DATABASE_URL is missing or invalid. See .env.example. ({detail})") from None
