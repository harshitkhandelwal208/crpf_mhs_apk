"""
Personnel model - operational profile for monitored personnel
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Float, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class PersonnelStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ON_LEAVE = "ON_LEAVE"
    DEPLOYED = "DEPLOYED"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Personnel(Base):
    __tablename__ = "personnel"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, unique=True
    )
    service_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    rank: Mapped[str] = mapped_column(String(50), nullable=False)
    unit: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[PersonnelStatus] = mapped_column(
        SAEnum(PersonnelStatus), nullable=False, default=PersonnelStatus.ACTIVE
    )
    risk_level: Mapped[RiskLevel] = mapped_column(
        SAEnum(RiskLevel), nullable=False, default=RiskLevel.LOW
    )
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_factors: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_check_in: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    user = relationship("User", back_populates="personnel", foreign_keys=[user_id])
    alerts = relationship("Alert", back_populates="personnel", lazy="select")
    journals = relationship("Journal", back_populates="personnel", lazy="select")
    assessments = relationship("Assessment", back_populates="personnel", lazy="select")

    @property
    def full_name(self) -> str:
        return f"{self.rank} {self.first_name} {self.last_name}"
