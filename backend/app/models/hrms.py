"""
HRMS Operational & Deployment Models
Tracks operational parameters critical to armed forces stress evaluation:
continuous deployments, irregular shifts, leave deprivation, hard postings, and transfer frequencies.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Float, Integer, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DutySchedule(Base):
    __tablename__ = "duty_schedules"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    personnel_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personnel.id"), nullable=False, index=True
    )
    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    shift_type: Mapped[str] = mapped_column(String(50), default="REGULAR")  # DAY, NIGHT, ROTATING, 24_HR
    hours_worked: Mapped[float] = mapped_column(Float, default=8.0)
    consecutive_days_on_duty: Mapped[int] = mapped_column(Integer, default=1)
    is_overtime: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    personnel = relationship("Personnel", back_populates="duty_schedules")


class LeaveRecord(Base):
    __tablename__ = "leave_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    personnel_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personnel.id"), nullable=False, index=True
    )
    leave_type: Mapped[str] = mapped_column(String(50), default="CASUAL")  # CASUAL, ANNUAL, MEDICAL, EMERGENCY
    applied_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")  # PENDING, APPROVED, REJECTED, CANCELLED
    rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    days_since_last_leave: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    personnel = relationship("Personnel", back_populates="leave_records")


class DeploymentHistory(Base):
    __tablename__ = "deployment_histories"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    personnel_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personnel.id"), nullable=False, index=True
    )
    deployment_name: Mapped[str] = mapped_column(String(100), nullable=False)
    terrain_type: Mapped[str] = mapped_column(
        String(50), default="STANDARD"
    )  # HIGH_ALTITUDE, JUNGLE, LWE_CONFLICT, CI_OPS, BORDER_OUTPOST
    hard_posting: Mapped[bool] = mapped_column(Boolean, default=True)
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_months: Mapped[float | None] = mapped_column(Float, nullable=True)
    family_separation_months: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    personnel = relationship("Personnel", back_populates="deployments")


class TransferRecord(Base):
    __tablename__ = "transfer_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    personnel_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personnel.id"), nullable=False, index=True
    )
    from_unit: Mapped[str] = mapped_column(String(100), nullable=False)
    to_unit: Mapped[str] = mapped_column(String(100), nullable=False)
    transfer_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    transfer_count_last_3_years: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    personnel = relationship("Personnel", back_populates="transfers")
