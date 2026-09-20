"""
Sentinel Backend - Configuration
"""
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
ENV_FILES = (
    PROJECT_ROOT / "env",
    PROJECT_ROOT / ".env",
    BACKEND_DIR / ".env",
)


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Sentinel API"
    APP_VERSION: str = "1.0.0"
    ENV: str = Field(
        default="development",
        validation_alias=AliasChoices("SENTINEL_ENV", "ENV"),
    )
    DEBUG: bool = False
    SQL_ECHO: bool = False

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "development", "dev")
        return bool(value)

    @field_validator("ENV", mode="before")
    @classmethod
    def normalize_environment(cls, value):
        return str(value).strip().lower()

    # Database
    DATABASE_URL: str = f"sqlite:///{(BACKEND_DIR / 'sentinel.db').as_posix()}"
    DB_SCHEMA: str = "crpf_mhs"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_TIMEOUT_SECONDS: int = 15
    DB_POOL_RECYCLE_SECONDS: int = 300

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, value):
        database_url = str(value).strip() if value is not None else ""
        if not database_url:
            return f"sqlite:///{(BACKEND_DIR / 'sentinel.db').as_posix()}"
        if database_url.startswith("postgres://"):
            return "postgresql://" + database_url.removeprefix("postgres://")
        return database_url

    @field_validator("DB_SCHEMA")
    @classmethod
    def validate_database_schema(cls, value: str) -> str:
        schema = value.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", schema):
            raise ValueError("DB_SCHEMA must be a valid PostgreSQL identifier")
        if schema.lower() in {"information_schema", "pg_catalog", "pg_toast", "public"}:
            raise ValueError("DB_SCHEMA must be a dedicated application schema")
        return schema

    # JWT
    SECRET_KEY: str = "dev-secret-key-change-in-production-immediately"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Browsers require CORS; Android and the desktop BFF do not. Production
    # therefore defaults to no cross-origin browser access.
    CORS_ORIGINS: str = ""

    @property
    def cors_origins(self) -> list[str]:
        raw = self.CORS_ORIGINS.strip()
        if not raw:
            if self.ENV in {"development", "test"}:
                return [
                    "http://localhost:3000",
                    "http://127.0.0.1:3000",
                    "http://localhost:5173",
                    "http://127.0.0.1:5173",
                ]
            return []

        if raw.startswith("["):
            parsed = json.loads(raw)
            if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
                raise ValueError("CORS_ORIGINS JSON must be an array of origins")
            origins = parsed
        else:
            origins = [item.strip() for item in raw.split(",") if item.strip()]

        normalized = []
        for origin in origins:
            if origin == "*":
                raise ValueError("CORS_ORIGINS cannot contain '*' when credentials are enabled")
            parsed_origin = urlsplit(origin)
            if (
                parsed_origin.scheme not in {"http", "https"}
                or not parsed_origin.netloc
                or parsed_origin.path not in {"", "/"}
                or parsed_origin.query
                or parsed_origin.fragment
                or parsed_origin.username
                or parsed_origin.password
            ):
                raise ValueError(f"Invalid CORS origin: {origin}")
            normalized.append(f"{parsed_origin.scheme}://{parsed_origin.netloc}")
        return list(dict.fromkeys(normalized))

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.ENV == "production":
            if not self.DATABASE_URL or not (
                self.DATABASE_URL.startswith("postgresql://")
                or self.DATABASE_URL.startswith("postgres://")
            ):
                raise ValueError("Production DATABASE_URL must be a valid PostgreSQL connection string")
            if (
                self.SECRET_KEY == "dev-secret-key-change-in-production-immediately"
                or len(self.SECRET_KEY) < 32
            ):
                raise ValueError("Production SECRET_KEY must contain at least 32 characters")
        return self

    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
