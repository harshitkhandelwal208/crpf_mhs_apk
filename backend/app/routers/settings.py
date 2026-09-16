"""
Settings router - environment info and system configuration.
SUPER_ADMIN only.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.config import settings
from app.models.user import User, UserRole
from app.models.personnel import Personnel
from app.models.alert import Alert
from app.auth.dependencies import require_role
from app.schemas.schemas import EnvironmentInfo

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/environment", response_model=EnvironmentInfo)
async def get_environment_info(
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """Get environment and system information. SUPER_ADMIN only."""
    db_type = "SQLite" if "sqlite" in settings.DATABASE_URL else "PostgreSQL"

    return EnvironmentInfo(
        app_name=settings.APP_NAME,
        app_version=settings.APP_VERSION,
        environment=settings.ENV,
        database_type=db_type,
        total_users=db.query(func.count(User.id)).scalar() or 0,
        total_personnel=db.query(func.count(Personnel.id)).scalar() or 0,
        total_alerts=db.query(func.count(Alert.id)).scalar() or 0,
    )
