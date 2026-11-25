"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the OG card service."""

    model_config = SettingsConfigDict(
        env_prefix="OG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "OG Card Service"
    host: str = "0.0.0.0"
    port: int = 8000

    github_api_base: str = "https://api.github.com"
    github_token: str | None = None
    default_github_owner: str | None = None

    request_timeout_seconds: float = 5.0
    metadata_cache_ttl_seconds: int = 900
    image_cache_ttl_seconds: int = 3600
    max_cache_items: int = 512


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
