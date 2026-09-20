"""
Voluntary Biometric & Wearable Physiological Indicators Model
Tracks sleep architecture, resting heart rate, HRV (RMSSD), and autonomic stress indices.
Privacy-guaranteed: Voluntary submission, encrypted at rest.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Float, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BiometricReading(Base):
    __tablename__ = "biometric_readings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    personnel_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personnel.id"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
    resting_heart_rate: Mapped[float | None] = mapped_column(Float, nullable=True)  # bpm
    heart_rate_variability: Mapped[float | None] = mapped_column(Float, nullable=True)  # RMSSD in ms
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)  # Total sleep duration
    sleep_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0 to 100
    deep_sleep_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rem_sleep_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stress_index: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0 to 100
    step_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    device_source: Mapped[str | None] = mapped_column(String(50), default="VOLUNTARY_WEARABLE")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    personnel = relationship("Personnel", back_populates="biometrics")
