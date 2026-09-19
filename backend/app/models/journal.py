"""
Journal model - clinical content (access requires explicit permission)
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Journal(Base):
    __tablename__ = "journals"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    personnel_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("personnel.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Daily Journal")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    mood: Mapped[str] = mapped_column(String(50), nullable=False, default="okay")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="SUBMITTED")
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_flagged: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    personnel = relationship("Personnel", back_populates="journals")
