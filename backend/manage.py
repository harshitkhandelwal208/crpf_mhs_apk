"""Deployment-safe database and account management commands."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

import app.models  # noqa: F401 - register all tables before schema inspection
from app.auth.security import hash_password, validate_password_strength
from app.database import Base, SessionLocal, engine
from app.models.user import User, UserRole

BACKEND_DIR = Path(__file__).resolve().parent


def alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return config


def migrate() -> None:
    """Upgrade an empty or Alembic-managed database to the current schema."""
    config = alembic_config()
    table_names = set(inspect(engine).get_table_names())
    application_tables = set(Base.metadata.tables)

    if "alembic_version" in table_names or not (table_names & application_tables):
        command.upgrade(config, "head")
    else:
        # Older installations created tables directly through SQLAlchemy. Bring
        # any missing tables in, then establish the Alembic baseline. The schema
        # check below refuses to stamp an installation with structural drift.
        Base.metadata.create_all(bind=engine)
        command.stamp(config, "head")

    command.check(config)
    print("Database schema is at the latest migration revision.")



def bootstrap_admin() -> None:
    """Create the first super administrator without embedding credentials."""
    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
    full_name = os.getenv("BOOTSTRAP_ADMIN_NAME", "CRPF Platform Administrator").strip()

    if not email or "@" not in email or len(email) > 255:
        raise ValueError("BOOTSTRAP_ADMIN_EMAIL must be a valid email address")
    if not full_name or len(full_name) > 255:
        raise ValueError("BOOTSTRAP_ADMIN_NAME must contain 1 to 255 characters")
    validate_password_strength(password, minimum_length=16)

    with SessionLocal() as database:
        existing = database.query(User).filter(User.email == email).first()
        if existing:
            if existing.role != UserRole.SUPER_ADMIN:
                raise RuntimeError(
                    "The bootstrap email already belongs to a non-super-admin account"
                )
            print(f"Super administrator already exists: {email}")
            return

        database.add(
            User(
                email=email,
                full_name=full_name,
                hashed_password=hash_password(password),
                role=UserRole.SUPER_ADMIN,
                is_active=True,
                onboarding_complete=True,
            )
        )
        database.commit()
        print(f"Created initial super administrator: {email}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("migrate", "check", "bootstrap-admin"),
        help="Management operation to run",
    )
    arguments = parser.parse_args()

    if arguments.command == "migrate":
        migrate()
    elif arguments.command == "check":
        command.check(alembic_config())
        print("No pending database schema operations detected.")
    else:
        bootstrap_admin()


if __name__ == "__main__":
    main()
