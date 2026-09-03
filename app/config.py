"""Environment-backed application configuration."""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Runtime settings loaded from environment variables."""

    app_name: str = Field(default="Data Engineering Learning Coach")
    environment: str = Field(default="development")
    database_url: str = Field(default="sqlite:///./data/learning_coach.db")
    log_level: str = Field(default="INFO")


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings object for the current process."""
    return Settings(
        app_name=os.getenv("APP_NAME", "Data Engineering Learning Coach"),
        environment=os.getenv("ENVIRONMENT", "development"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./data/learning_coach.db"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
