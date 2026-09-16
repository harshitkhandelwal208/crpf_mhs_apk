"""
User model - core identity and role storage
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class UserRole(str, enum.Enum):
    PERSONNEL = "PERSONNEL"
    SUPERVISOR = "SUPERVISOR"
    MENTAL_HEALTH_PROFESSIONAL = "MENTAL_HEALTH_PROFESSIONAL"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


# Hierarchy for role comparison
ROLE_HIERARCHY = {
    UserRole.PERSONNEL: 0,
    UserRole.SUPERVISOR: 1,
    UserRole.MENTAL_HEALTH_PROFESSIONAL: 1,
    UserRole.ADMIN: 2,
    UserRole.SUPER_ADMIN: 3,
}


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole), nullable=False, default=UserRole.PERSONNEL
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    permissions = relationship("Permission", back_populates="user", lazy="selectin")
    refresh_tokens = relationship("RefreshToken", back_populates="user", lazy="select")

    def has_minimum_role(self, required_role: UserRole) -> bool:
        """Check if user's role meets the minimum required role level."""
        return ROLE_HIERARCHY.get(self.role, 0) >= ROLE_HIERARCHY.get(required_role, 0)
