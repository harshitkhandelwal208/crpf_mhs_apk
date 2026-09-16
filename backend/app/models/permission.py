"""
Permission model - explicit permission grants for sensitive content.

ADMIN role does NOT automatically receive clinical permissions.
Clinical access (journals, assessments, AI conversations, transcripts)
must be granted explicitly per-user via this table.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("user_id", "resource", "action", name="uq_user_permission"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    resource: Mapped[str] = mapped_column(String(100), nullable=False)
    # e.g., "clinical:journals", "clinical:assessments",
    #        "clinical:ai_conversations", "clinical:transcripts"
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    # e.g., "read", "write", "delete"
    granted: Mapped[bool] = mapped_column(Boolean, default=True)
    granted_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="permissions")
    granter = relationship("User", foreign_keys=[granted_by])
