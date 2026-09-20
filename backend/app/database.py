"""
Sentinel Backend - Database session management
"""
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema

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

if not is_sqlite:
    @event.listens_for(engine, "connect")
    def set_application_schema(dbapi_connection, _connection_record) -> None:
        """Keep all FastAPI tables isolated from legacy/public database tables."""
        previous_autocommit = dbapi_connection.autocommit
        dbapi_connection.autocommit = True
        try:
            with dbapi_connection.cursor() as cursor:
                cursor.execute(
                    f'SET SESSION search_path TO "{settings.DB_SCHEMA}"'
                )
        finally:
            dbapi_connection.autocommit = previous_autocommit

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def ensure_database_schema() -> None:
    """Create the dedicated PostgreSQL schema before pooled connections use it."""
    if is_sqlite:
        return

    bootstrap_engine = create_engine(settings.DATABASE_URL, poolclass=NullPool)
    try:
        with bootstrap_engine.begin() as connection:
            connection.execute(CreateSchema(settings.DB_SCHEMA, if_not_exists=True))
    finally:
        bootstrap_engine.dispose()


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
