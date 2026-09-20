"""
Alert model - risk alerts and workflow states
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class AlertSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, enum.Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class AlertType(str, enum.Enum):
    BEHAVIORAL = "BEHAVIORAL"
    CHECK_IN_MISSED = "CHECK_IN_MISSED"
    RISK_SCORE_CHANGE = "RISK_SCORE_CHANGE"
    ASSESSMENT_DUE = "ASSESSMENT_DUE"
    AI_FLAGGED = "AI_FLAGGED"
    MANUAL = "MANUAL"
    SYSTEM = "SYSTEM"


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    personnel_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personnel.id"), nullable=False, index=True
    )
    type: Mapped[AlertType] = mapped_column(
        SAEnum(AlertType), nullable=False
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        SAEnum(AlertSeverity), nullable=False
    )
    status: Mapped[AlertStatus] = mapped_column(
        SAEnum(AlertStatus), nullable=False, default=AlertStatus.OPEN
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    acknowledged_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    escalation_required: Mapped[bool] = mapped_column(default=False)
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
    personnel = relationship("Personnel", back_populates="alerts")
    assignee = relationship("User", foreign_keys=[assigned_to])
    acknowledger = relationship("User", foreign_keys=[acknowledged_by])
    interventions = relationship("WelfareIntervention", back_populates="alert", lazy="select")
