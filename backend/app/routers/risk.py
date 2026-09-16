"""
Risk dashboard router - aggregated risk views.
Raw risk scores hidden from non-authorized roles.
Personnel users never see internal risk levels.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.user import User, UserRole
from app.models.personnel import Personnel, RiskLevel
from app.models.alert import Alert, AlertStatus
from app.auth.dependencies import require_role
from app.schemas.schemas import (
    RiskDashboardResponse,
    PersonnelRiskResponse,
    RiskDistribution,
    PersonnelResponse,
    AlertResponse,
)

router = APIRouter(prefix="/risk", tags=["Risk Dashboard"])


@router.get("/dashboard", response_model=RiskDashboardResponse)
async def get_risk_dashboard(
    current_user: User = Depends(require_role(UserRole.SUPERVISOR)),
    db: Session = Depends(get_db),
):
    """Aggregated risk dashboard. No raw scores for unauthorized roles."""
    total = db.query(func.count(Personnel.id)).scalar() or 0

    # Risk distribution
    dist = {}
    for level in RiskLevel:
        count = db.query(func.count(Personnel.id)).filter(
            Personnel.risk_level == level
        ).scalar() or 0
        dist[level.value.lower()] = count

    # High-risk personnel
    high_risk = (
        db.query(Personnel)
        .filter(Personnel.risk_level.in_([RiskLevel.HIGH, RiskLevel.CRITICAL]))
        .order_by(Personnel.risk_score.desc())
        .limit(10)
        .all()
    )

    # Recent risk-related alerts
    recent_alerts = (
        db.query(Alert)
        .filter(Alert.type == "RISK_SCORE_CHANGE")
        .order_by(Alert.created_at.desc())
        .limit(10)
        .all()
    )

    # Unit summary
    units = (
        db.query(
            Personnel.unit,
            func.count(Personnel.id).label("total"),
            func.avg(Personnel.risk_score).label("avg_risk"),
        )
        .group_by(Personnel.unit)
        .all()
    )
    units_summary = [
        {"unit": u.unit, "total": u.total, "avg_risk_score": round(u.avg_risk or 0, 2)}
        for u in units
    ]

    return RiskDashboardResponse(
        total_personnel=total,
        distribution=RiskDistribution(**dist),
        high_risk_personnel=high_risk,
        recent_risk_changes=[],  # Simplified - full implementation would convert to AlertResponse
        units_summary=units_summary,
    )


@router.get("/personnel/{personnel_id}", response_model=PersonnelRiskResponse)
async def get_personnel_risk(
    personnel_id: str,
    current_user: User = Depends(require_role(UserRole.SUPERVISOR)),
    db: Session = Depends(get_db),
):
    """Get risk details for a specific personnel member.
    Raw risk score only shown to MHP and SUPER_ADMIN."""
    person = db.query(Personnel).filter(Personnel.id == personnel_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Personnel not found")

    show_raw = current_user.role in (
        UserRole.MENTAL_HEALTH_PROFESSIONAL,
        UserRole.SUPER_ADMIN,
    )

    recent_alerts = (
        db.query(Alert)
        .filter(Alert.personnel_id == personnel_id)
        .order_by(Alert.created_at.desc())
        .limit(5)
        .all()
    )

    risk_factors = []
    if person.risk_factors:
        risk_factors = [f.strip() for f in person.risk_factors.split(",")]

    return PersonnelRiskResponse(
        personnel_id=person.id,
        risk_level=person.risk_level,
        risk_score=person.risk_score if show_raw else None,
        risk_factors=risk_factors if show_raw else [],
        recent_alerts=[],  # Simplified
        trend="STABLE",
    )
