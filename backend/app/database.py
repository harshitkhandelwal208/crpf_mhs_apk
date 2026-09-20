"""
Sentinel Backend - Database session management
"""
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


is_sqlite = settings.DATABASE_URL.startswith("sqlite")
engine_options: dict[str, Any] = {
    "echo": settings.SQL_ECHO,
}

if is_sqlite:
    # SQLite is used for local development and tests.
    engine_options["connect_args"] = {"check_same_thread": False}
else:
    # Cloud PostgreSQL connections can go stale while an instance is idle.
    engine_options.update({
        "pool_pre_ping": True,
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT_SECONDS,
        "pool_recycle": settings.DB_POOL_RECYCLE_SECONDS,
    })

engine = create_engine(settings.DATABASE_URL, **engine_options)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
