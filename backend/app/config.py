"""
Sentinel Backend - Configuration
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Sentinel API"
    APP_VERSION: str = "1.0.0"
    ENV: str = os.getenv("SENTINEL_ENV", "development")
    DEBUG: bool = ENV == "development"

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
        "http://127.0.0.1:5173",
        "http://10.0.2.2:8000",   # Android emulator
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
