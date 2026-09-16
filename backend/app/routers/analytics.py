"""
Analytics router - aggregated metrics for ADMIN+ users.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.user import User, UserRole
from app.models.personnel import Personnel, PersonnelStatus, RiskLevel
from app.models.alert import Alert, AlertStatus
from app.auth.dependencies import require_role
from app.schemas.schemas import (
    AnalyticsOverview,
    AnalyticsTrendsResponse,
    AnalyticsTrend,
    RiskDistribution,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
async def get_analytics_overview(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """High-level analytics overview."""
    total_personnel = db.query(func.count(Personnel.id)).scalar() or 0
    active_personnel = (
        db.query(func.count(Personnel.id))
        .filter(Personnel.status == PersonnelStatus.ACTIVE)
        .scalar() or 0
    )
    total_alerts = db.query(func.count(Alert.id)).scalar() or 0
    open_alerts = (
        db.query(func.count(Alert.id))
        .filter(Alert.status.in_([
            AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED,
            AlertStatus.ASSIGNED, AlertStatus.IN_PROGRESS,
        ]))
        .scalar() or 0
    )
    resolved_alerts = (
        db.query(func.count(Alert.id))
        .filter(Alert.status == AlertStatus.RESOLVED)
        .scalar() or 0
    )

    # Average resolution time
    avg_hours = 24.0  # Default placeholder

    # Risk distribution
    dist = {}
    for level in RiskLevel:
        count = db.query(func.count(Personnel.id)).filter(
            Personnel.risk_level == level
        ).scalar() or 0
        dist[level.value.lower()] = count

    return AnalyticsOverview(
        total_personnel=total_personnel,
        active_personnel=active_personnel,
        total_alerts=total_alerts,
        open_alerts=open_alerts,
        resolved_alerts=resolved_alerts,
        avg_resolution_hours=avg_hours,
        risk_distribution=RiskDistribution(**dist),
    )


@router.get("/trends", response_model=AnalyticsTrendsResponse)
async def get_analytics_trends(
    days: int = Query(30, ge=7, le=365),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Alert and risk trends over time."""
    trends = []
    now = datetime.now(timezone.utc)

    for i in range(days):
        date = now - timedelta(days=days - 1 - i)
        date_str = date.strftime("%Y-%m-%d")
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        alert_count = (
            db.query(func.count(Alert.id))
            .filter(Alert.created_at >= start, Alert.created_at < end)
            .scalar() or 0
        )

        trends.append(AnalyticsTrend(
            date=date_str,
            alert_count=alert_count,
            risk_score_avg=0.0,
        ))

    return AnalyticsTrendsResponse(trends=trends, period=f"{days}_days")


@router.get("/risk-distribution")
async def get_risk_distribution(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Risk level distribution with unit breakdown."""
    units = (
        db.query(
            Personnel.unit,
            Personnel.risk_level,
            func.count(Personnel.id).label("count"),
        )
        .group_by(Personnel.unit, Personnel.risk_level)
        .all()
    )

    result = {}
    for row in units:
        if row.unit not in result:
            result[row.unit] = {"unit": row.unit, "low": 0, "moderate": 0, "high": 0, "critical": 0}
        result[row.unit][row.risk_level.lower()] = row.count

    return list(result.values())
