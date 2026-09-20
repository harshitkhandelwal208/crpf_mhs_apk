"""
Alerts router - CRUD + workflow actions (acknowledge, assign, status, resolve).
"""
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.personnel import Personnel
from app.auth.dependencies import require_role
from app.schemas.schemas import (
    AlertResponse,
    AlertCreateRequest,
    AlertAssignRequest,
    AlertStatusChangeRequest,
    AlertResolveRequest,
    AlertListResponse,
    MessageResponse,
)

router = APIRouter(prefix="/alerts", tags=["Alerts"])


def _alert_to_response(alert: Alert, db: Session) -> AlertResponse:
    """Convert Alert model to response DTO with related names."""
    personnel = db.query(Personnel).filter(Personnel.id == alert.personnel_id).first()
    assignee = None
    if alert.assigned_to:
        assignee_user = db.query(User).filter(User.id == alert.assigned_to).first()
        assignee = assignee_user.full_name if assignee_user else None

    return AlertResponse(
        id=alert.id,
        personnel_id=alert.personnel_id,
        personnel_name=personnel.full_name if personnel else None,
        type=alert.type,
        severity=alert.severity,
        status=alert.status,
        title=alert.title,
        description=alert.description,
        assigned_to=alert.assigned_to,
        assignee_name=assignee,
        acknowledged_by=alert.acknowledged_by,
        acknowledged_at=alert.acknowledged_at,
        resolution_notes=alert.resolution_notes,
        resolved_at=alert.resolved_at,
        escalation_required=alert.escalation_required,
        created_at=alert.created_at,
    )


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status: AlertStatus | None = Query(None),
    severity: AlertSeverity | None = Query(None),
    alert_type: AlertType | None = Query(None, alias="type"),
    personnel_id: str | None = Query(None),
    assigned_to: str | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(require_role(UserRole.SUPERVISOR)),
    db: Session = Depends(get_db),
):
    """List alerts with filters, pagination, and sorting."""
    query = db.query(Alert)

    if status:
        query = query.filter(Alert.status == status)
    if severity:
        query = query.filter(Alert.severity == severity)
    if alert_type:
        query = query.filter(Alert.type == alert_type)
    if personnel_id:
        query = query.filter(Alert.personnel_id == personnel_id)
    if assigned_to:
        query = query.filter(Alert.assigned_to == assigned_to)

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    sort_column = getattr(Alert, sort_by, Alert.created_at)
    if sort_order == "desc":
        sort_column = sort_column.desc()
    query = query.order_by(sort_column)

    offset = (page - 1) * page_size
    alerts = query.offset(offset).limit(page_size).all()

    return AlertListResponse(
        items=[_alert_to_response(a, db) for a in alerts],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    current_user: User = Depends(require_role(UserRole.SUPERVISOR)),
    db: Session = Depends(get_db),
):
    """Get single alert detail."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _alert_to_response(alert, db)


@router.post("", response_model=AlertResponse, status_code=201)
async def create_alert(
    body: AlertCreateRequest,
    current_user: User = Depends(require_role(UserRole.SUPERVISOR)),
    db: Session = Depends(get_db),
):
    """Create a new alert."""
    personnel = db.query(Personnel).filter(Personnel.id == body.personnel_id).first()
    if not personnel:
        raise HTTPException(status_code=404, detail="Personnel not found")

    alert = Alert(
        personnel_id=body.personnel_id,
        type=body.type,
        severity=body.severity,
        title=body.title,
        description=body.description,
        escalation_required=body.escalation_required,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return _alert_to_response(alert, db)


@router.put("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: str,
    current_user: User = Depends(require_role(UserRole.SUPERVISOR)),
    db: Session = Depends(get_db),
):
    """Acknowledge an alert."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert.status != AlertStatus.OPEN:
        raise HTTPException(
            status_code=400,
            detail="Only OPEN alerts can be acknowledged",
        )

    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return _alert_to_response(alert, db)


@router.put("/{alert_id}/assign", response_model=AlertResponse)
async def assign_alert(
    alert_id: str,
    body: AlertAssignRequest,
    current_user: User = Depends(require_role(UserRole.SUPERVISOR)),
    db: Session = Depends(get_db),
):
    """Assign an alert to a user."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    assignee = db.query(User).filter(User.id == body.assigned_to).first()
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee user not found")

    alert.assigned_to = body.assigned_to
    if alert.status in (AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED):
        alert.status = AlertStatus.ASSIGNED
    db.commit()
    db.refresh(alert)
    return _alert_to_response(alert, db)


@router.put("/{alert_id}/status", response_model=AlertResponse)
async def change_alert_status(
    alert_id: str,
    body: AlertStatusChangeRequest,
    current_user: User = Depends(require_role(UserRole.SUPERVISOR)),
    db: Session = Depends(get_db),
):
    """Change alert status."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = body.status
    db.commit()
    db.refresh(alert)
    return _alert_to_response(alert, db)


@router.put("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: str,
    body: AlertResolveRequest,
    current_user: User = Depends(require_role(UserRole.SUPERVISOR)),
    db: Session = Depends(get_db),
):
    """Resolve an alert with notes."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = AlertStatus.RESOLVED
    alert.resolution_notes = body.resolution_notes
    alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return _alert_to_response(alert, db)
