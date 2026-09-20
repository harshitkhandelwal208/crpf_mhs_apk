"""
Welfare Interventions API Router
Manages non-punitive, supportive intervention recommendations:
Rest rotations, peer-buddy pairings, tele-counseling sessions, family connect, and leave fast-tracking.
"""
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.personnel import Personnel
from app.models.intervention import WelfareIntervention
from app.schemas.schemas import WelfareInterventionResponse, InterventionStatusUpdate

router = APIRouter(prefix="/interventions", tags=["Welfare Interventions"])


@router.get("/personnel/{personnel_id}", response_model=List[WelfareInterventionResponse])
def get_personnel_interventions(
    personnel_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    personnel = db.get(Personnel, personnel_id)
    if not personnel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personnel not found")

    interventions = db.scalars(
        select(WelfareIntervention)
        .where(WelfareIntervention.personnel_id == personnel_id)
        .order_by(desc(WelfareIntervention.created_at))
    ).all()
    return interventions


@router.get("/alert/{alert_id}", response_model=List[WelfareInterventionResponse])
def get_alert_interventions(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interventions = db.scalars(
        select(WelfareIntervention)
        .where(WelfareIntervention.alert_id == alert_id)
        .order_by(desc(WelfareIntervention.created_at))
    ).all()
    return interventions


@router.patch("/{intervention_id}", response_model=WelfareInterventionResponse)
def update_intervention_status(
    intervention_id: str,
    payload: InterventionStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    intervention = db.get(WelfareIntervention, intervention_id)
    if not intervention:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intervention not found")

    intervention.status = payload.status
    if payload.outcome_notes:
        intervention.outcome_notes = payload.outcome_notes
    intervention.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(intervention)
    return intervention
