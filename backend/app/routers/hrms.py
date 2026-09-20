"""
HRMS Operational & Deployment Data API Router
Enables integration with Armed Forces personnel records: shifts, leave, deployment, transfers.
Computes Explainable Operational Fatigue & Burnout Metrics.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.personnel import Personnel
from app.models.hrms import DutySchedule, LeaveRecord, DeploymentHistory, TransferRecord
from app.schemas.schemas import (
    HRMSProfileResponse,
    DutyScheduleCreate,
    DutyScheduleResponse,
    LeaveRecordCreate,
    LeaveRecordResponse,
    DeploymentCreate,
    DeploymentResponse,
    HolisticRiskAssessmentResponse,
)
from app.services.hrms_engine import evaluate_hrms_stress
from app.services.risk_engine import compute_holistic_personnel_risk

router = APIRouter(prefix="/personnel", tags=["HRMS Operational Records"])


@router.get("/{personnel_id}/hrms-profile", response_model=HRMSProfileResponse)
def get_personnel_hrms_profile(
    personnel_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    personnel = db.get(Personnel, personnel_id)
    if not personnel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personnel not found")

    result = evaluate_hrms_stress(db, personnel_id)
    return HRMSProfileResponse(
        personnel_id=personnel_id,
        operational_stress_score=result["operational_stress_score"],
        burnout_level=result["burnout_level"],
        contributing_factors=result["contributing_factors"],
        metrics=result["metrics"],
        insights=result["insights"],
        recommendations=result["recommendations"],
    )


@router.get("/{personnel_id}/holistic-risk", response_model=HolisticRiskAssessmentResponse)
def get_holistic_risk_profile(
    personnel_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    personnel = db.get(Personnel, personnel_id)
    if not personnel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personnel not found")

    assessment = compute_holistic_personnel_risk(db, personnel_id)
    return HolisticRiskAssessmentResponse(
        personnel_id=personnel_id,
        composite_risk_score=assessment["composite_risk_score"],
        risk_level=assessment["risk_level"],
        xai_factor_breakdown=assessment["xai_factor_breakdown"],
        hrms_details=assessment["hrms_details"],
        timestamp=assessment["timestamp"],
    )


@router.post("/{personnel_id}/duty-schedule", response_model=DutyScheduleResponse)
def log_duty_schedule(
    personnel_id: str,
    payload: DutyScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    personnel = db.get(Personnel, personnel_id)
    if not personnel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personnel not found")

    record = DutySchedule(
        personnel_id=personnel_id,
        shift_type=payload.shift_type,
        hours_worked=payload.hours_worked,
        consecutive_days_on_duty=payload.consecutive_days_on_duty,
        is_overtime=payload.is_overtime,
        notes=payload.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.post("/{personnel_id}/leave-record", response_model=LeaveRecordResponse)
def log_leave_record(
    personnel_id: str,
    payload: LeaveRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    personnel = db.get(Personnel, personnel_id)
    if not personnel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personnel not found")

    record = LeaveRecord(
        personnel_id=personnel_id,
        leave_type=payload.leave_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=payload.status,
        rejection_reason=payload.rejection_reason,
        days_since_last_leave=payload.days_since_last_leave,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.post("/{personnel_id}/deployment", response_model=DeploymentResponse)
def log_deployment_history(
    personnel_id: str,
    payload: DeploymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    personnel = db.get(Personnel, personnel_id)
    if not personnel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personnel not found")

    record = DeploymentHistory(
        personnel_id=personnel_id,
        deployment_name=payload.deployment_name,
        terrain_type=payload.terrain_type,
        hard_posting=payload.hard_posting,
        start_date=payload.start_date,
        end_date=payload.end_date,
        duration_months=payload.duration_months,
        family_separation_months=payload.family_separation_months,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
