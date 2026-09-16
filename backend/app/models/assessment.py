"""
Assessment model - clinical assessments (access requires explicit permission)
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text, Float, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class AssessmentType(str, enum.Enum):
    PHQ9 = "PHQ9"
    GAD7 = "GAD7"
    PCL5 = "PCL5"
    AUDIT_C = "AUDIT_C"
    COLUMBIA = "COLUMBIA"
    CUSTOM = "CUSTOM"


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    personnel_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personnel.id"), nullable=False, index=True
    )
    type: Mapped[AssessmentType] = mapped_column(
        SAEnum(AssessmentType), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_indicators: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessed_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    personnel = relationship("Personnel", back_populates="assessments")
    assessor = relationship("User", foreign_keys=[assessed_by])
