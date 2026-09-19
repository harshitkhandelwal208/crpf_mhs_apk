"""
Sentinel Backend - Configuration
"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Sentinel API"
    APP_VERSION: str = "1.0.0"
    ENV: str = os.getenv("SENTINEL_ENV", "development")
    DEBUG: bool = True

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v):
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "development", "dev")
        return bool(v)

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "sqlite:///./sentinel.db"
    )

    # JWT
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "dev-secret-key-change-in-production-immediately"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # Alternate dev
        "*",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://10.0.2.2:8000",   # Android emulator
        "http://127.0.0.1:8088",
        "http://localhost:8088",
        "http://10.0.2.2:8000",
    ]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


settings = Settings()
