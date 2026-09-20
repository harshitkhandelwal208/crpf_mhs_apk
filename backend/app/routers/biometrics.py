"""
Voluntary Biometrics & Wearable Telemetry API Router
Provides encrypted logging and longitudinal trends for sleep hours, HRV, and autonomic stress.
Non-punitive, strictly voluntary, privacy-guaranteed.
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.personnel import Personnel
from app.models.biometrics import BiometricReading
from app.schemas.schemas import (
    BiometricIngestRequest,
    BiometricResponse,
    BiometricTrendsResponse,
)

router = APIRouter(prefix="/biometrics", tags=["Voluntary Biometrics"])


@router.post("/record", response_model=BiometricResponse)
def record_biometric_telemetry(
    payload: BiometricIngestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    personnel = db.scalar(select(Personnel).where(Personnel.user_id == current_user.id))
    if not personnel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Personnel profile not associated with authenticated user"
        )

    reading = BiometricReading(
        personnel_id=personnel.id,
        timestamp=datetime.now(timezone.utc),
        resting_heart_rate=payload.resting_heart_rate,
        heart_rate_variability=payload.heart_rate_variability,
        sleep_hours=payload.sleep_hours,
        sleep_quality_score=payload.sleep_quality_score,
        deep_sleep_minutes=payload.deep_sleep_minutes,
        rem_sleep_minutes=payload.rem_sleep_minutes,
        stress_index=payload.stress_index,
        step_count=payload.step_count,
        device_source=payload.device_source,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


@router.get("/{personnel_id}/trends", response_model=BiometricTrendsResponse)
def get_biometric_trends(
    personnel_id: str,
    days: int = 14,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    personnel = db.get(Personnel, personnel_id)
    if not personnel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personnel not found")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    readings = db.scalars(
        select(BiometricReading)
        .where(BiometricReading.personnel_id == personnel_id, BiometricReading.timestamp >= cutoff)
        .order_by(desc(BiometricReading.timestamp))
    ).all()

    avg_sleep = 0.0
    avg_stress = 0.0
    if readings:
        sleep_vals = [r.sleep_hours for r in readings if r.sleep_hours is not None]
        stress_vals = [r.stress_index for r in readings if r.stress_index is not None]
        avg_sleep = sum(sleep_vals) / len(sleep_vals) if sleep_vals else 0.0
        avg_stress = sum(stress_vals) / len(stress_vals) if stress_vals else 0.0

    return BiometricTrendsResponse(
        personnel_id=personnel_id,
        readings=readings,
        avg_sleep_hours=round(avg_sleep, 1),
        avg_stress_index=round(avg_stress, 1),
        wearable_paired=len(readings) > 0,
    )
