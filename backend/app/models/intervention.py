"""
Welfare Intervention Model
Provides non-punitive, supportive intervention workflows:
Peer buddy pairing, mandatory rest rotations, counseling support, and leave fast-tracking.
Captures Explainable AI (XAI) contributing factor weights for full organizational transparency.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WelfareIntervention(Base):
    __tablename__ = "welfare_interventions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    personnel_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personnel.id"), nullable=False, index=True
    )
    alert_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("alerts.id"), nullable=True, index=True
    )
    category: Mapped[str] = mapped_column(
        String(50), default="REST_ROTATION"
    )  # REST_ROTATION, PEER_BUDDY, COUNSELING, FAMILY_CONNECT, LEAVE_EXPEDITE, DE_ESCALATION
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    action_plan: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="PRIORITY")  # ROUTINE, PRIORITY, URGENT
    status: Mapped[str] = mapped_column(
        String(50), default="RECOMMENDED"
    )  # RECOMMENDED, INITIATED, IN_PROGRESS, COMPLETED, DECLINED

    # Explainable AI (XAI) transparent attribution
    recommended_by_xai: Mapped[bool] = mapped_column(Boolean, default=True)
    contributing_factors: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON representation of feature attribution weights

    assigned_officer_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    outcome_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    personnel = relationship("Personnel", back_populates="interventions")
    alert = relationship("Alert", back_populates="interventions")
    assigned_officer = relationship("User", foreign_keys=[assigned_officer_id])
