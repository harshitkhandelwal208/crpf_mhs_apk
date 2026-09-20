"""
Compatibility API for the Next.js administration console.

All operational and clinical data comes from the same SQLAlchemy models used by
mobile clients. Clinical sections are permission-gated and personnel detail
access is audited.
"""
import json
import math
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.auth.dependencies import require_role
from app.auth.security import hash_password, validate_password_strength
from app.database import get_db
from app.models.ai import AIConversation, AIMessage
from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.assessment import Assessment
from app.models.audit_log import AuditLog
from app.models.journal import Journal
from app.models.personnel import Personnel, PersonnelStatus, RiskLevel
from app.models.support import SupportRequest
from app.models.user import User, UserRole
from app.models.voice import VoiceEntry

router = APIRouter(prefix="/admin", tags=["Admin Console Compatibility"])

RISK_LEVELS = (
    RiskLevel.LOW,
    RiskLevel.MODERATE,
    RiskLevel.HIGH,
    RiskLevel.CRITICAL,
)
UI_RISK_LEVELS = ("NORMAL", "LOW", "MODERATE", "ELEVATED", "HIGH", "CRITICAL")
RISK_COLORS = {
    "NORMAL": "#059669",
    "LOW": "#0d9488",
    "MODERATE": "#d97706",
    "ELEVATED": "#ea580c",
    "HIGH": "#dc2626",
    "CRITICAL": "#9f1239",
}
RISK_LABELS = {level: level.title() for level in UI_RISK_LEVELS}
OPEN_ALERT_STATUSES = (
    AlertStatus.OPEN,
    AlertStatus.ACKNOWLEDGED,
    AlertStatus.ASSIGNED,
    AlertStatus.IN_PROGRESS,
)
CLINICAL_RESOURCES = {
    "journals": "clinical:journals",
    "assessments": "clinical:assessments",
    "conversations": "clinical:ai_conversations",
    "voiceEntries": "clinical:transcripts",
}


class AdminAlertUpdate(BaseModel):
    status: str | None = None
    assignedToId: str | None = None


class AdminPersonnelCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    fullName: str = Field(min_length=2, max_length=255)
    serviceNumber: str = Field(min_length=2, max_length=50)
    rank: str = Field(min_length=1, max_length=50)
    unit: str = Field(min_length=1, max_length=100)
    initialPassword: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized):
            raise ValueError("Enter a valid email address")
        return normalized

    @field_validator("fullName", "serviceNumber", "rank", "unit")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Value cannot be blank")
        return normalized

    @field_validator("initialPassword")
    @classmethod
    def validate_initial_password(cls, value: str) -> str:
        validate_password_strength(value)
        return value


def _risk_distribution_dto(counts: dict[RiskLevel, int]) -> list[dict]:
    return [
        {
            "level": level,
            "label": RISK_LABELS[level],
            "count": counts.get(RiskLevel(level), 0)
            if level in RiskLevel._value2member_map_
            else 0,
            "color": RISK_COLORS[level],
        }
        for level in UI_RISK_LEVELS
    ]


def _risk_counts(query) -> dict[RiskLevel, int]:
    rows = (
        query.with_entities(
            Personnel.risk_level,
            func.count(Personnel.id),
        )
        .group_by(Personnel.risk_level)
        .all()
    )
    return {level: count for level, count in rows}


def _ui_alert_severity(severity: AlertSeverity) -> str:
    if severity == AlertSeverity.MEDIUM:
        return RiskLevel.MODERATE.value
    return severity.value


def _risk_level_for_alert(severity: AlertSeverity) -> RiskLevel:
    if severity == AlertSeverity.MEDIUM:
        return RiskLevel.MODERATE
    return RiskLevel(severity.value)


def _ui_alert_status(alert_status: AlertStatus) -> str:
    if alert_status in (AlertStatus.ASSIGNED, AlertStatus.IN_PROGRESS):
        return "IN_REVIEW"
    return alert_status.value


def _alert_to_dto(alert: Alert) -> dict:
    person = alert.personnel
    assignee = alert.assignee
    return {
        "id": alert.id,
        "userId": alert.personnel_id,
        "userName": person.full_name if person else "Unknown personnel",
        "userUnit": person.unit if person else None,
        "severity": _ui_alert_severity(alert.severity),
        "status": _ui_alert_status(alert.status),
        "reason": alert.description or alert.title,
        "source": alert.type.value.lower(),
        "assignedTo": assignee.full_name if assignee else None,
        "createdAt": alert.created_at,
        "resolvedAt": alert.resolved_at,
    }


def _clinical_visibility(current_user: User) -> dict[str, bool]:
    if current_user.role in (
        UserRole.MENTAL_HEALTH_PROFESSIONAL,
        UserRole.SUPER_ADMIN,
    ):
        return {section: True for section in CLINICAL_RESOURCES}

    grants = {
        permission.resource
        for permission in current_user.permissions
        if permission.action == "read" and permission.granted
    }
    return {
        section: resource in grants
        for section, resource in CLINICAL_RESOURCES.items()
    }


def _raw_risk_visible(current_user: User) -> bool:
    return current_user.role in (
        UserRole.MENTAL_HEALTH_PROFESSIONAL,
        UserRole.SUPER_ADMIN,
    )


def _personnel_status(person: Personnel) -> str:
    if person.user and not person.user.is_active:
        return "SUSPENDED"
    if person.status in (PersonnelStatus.SUSPENDED, PersonnelStatus.INACTIVE):
        return "SUSPENDED"
    return "ACTIVE"


def _personnel_row_dto(person: Personnel) -> dict:
    return {
        "id": person.id,
        "name": person.full_name,
        "serviceNumber": person.service_number,
        "unit": person.unit,
        "role": "USER",
        "status": _personnel_status(person),
        "wellbeingLevel": person.risk_level.value,
        "lastCheckIn": person.last_check_in,
        "lastActivity": person.last_check_in or person.updated_at,
    }


def _support_status(value: str) -> str:
    return {"PENDING": "OPEN", "IN_REVIEW": "ASSIGNED", "RESOLVED": "RESOLVED"}.get(
        value, "OPEN"
    )


def _score_level(score: float, max_score: float) -> str:
    normalized = 0.0 if max_score <= 0 else (score / max_score) * 100
    if normalized < 20:
        return "LOW"
    if normalized < 50:
        return "MODERATE"
    if normalized < 75:
        return "HIGH"
    return "CRITICAL"


def _parse_alert_status(value: str) -> tuple[AlertStatus, ...]:
    normalized = value.upper()
    if normalized == "IN_REVIEW":
        return (AlertStatus.ASSIGNED, AlertStatus.IN_PROGRESS)
    try:
        return (AlertStatus(normalized),)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported alert status: {value}",
        ) from exc


def _parse_alert_severity(value: str) -> AlertSeverity:
    normalized = value.upper()
    if normalized == RiskLevel.MODERATE.value:
        normalized = AlertSeverity.MEDIUM.value
    try:
        return AlertSeverity(normalized)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported alert severity: {value}",
        ) from exc


def _parse_update_status(value: str) -> AlertStatus:
    normalized = value.upper()
    if normalized == "IN_REVIEW":
        return AlertStatus.IN_PROGRESS
    try:
        return AlertStatus(normalized)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported alert status: {value}",
        ) from exc


def _redact_metadata(value):
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(word in lowered for word in ("password", "token", "secret", "key")):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = _redact_metadata(item)
        return redacted
    if isinstance(value, list):
        return [_redact_metadata(item) for item in value]
    return value


def _safe_audit_metadata(details: str | None):
    if not details:
        return None
    try:
        return _redact_metadata(json.loads(details))
    except (json.JSONDecodeError, TypeError):
        lowered = details.lower()
        if any(word in lowered for word in ("password", "token", "secret", "key")):
            return {"redacted": True}
        return {"details": details}


@router.get("/dashboard")
async def get_admin_dashboard(
    current_user: User = Depends(require_role(UserRole.SUPERVISOR)),
    db: Session = Depends(get_db),
):
    personnel_query = db.query(Personnel)
    counts = _risk_counts(personnel_query)

    total_personnel = db.query(func.count(Personnel.id)).scalar() or 0
    active_users = (
        db.query(func.count(Personnel.id))
        .filter(Personnel.status == PersonnelStatus.ACTIVE)
        .scalar()
        or 0
    )
    assessments_completed = db.query(func.count(Assessment.id)).scalar() or 0
    critical_alerts = (
        db.query(func.count(Alert.id))
        .filter(
            Alert.severity == AlertSeverity.CRITICAL,
            Alert.status.in_(OPEN_ALERT_STATUSES),
        )
        .scalar()
        or 0
    )

    return {
        "cards": {
            "totalPersonnel": total_personnel,
            "activeUsers": active_users,
            "assessmentsCompleted": assessments_completed,
            "elevatedIndicators": 0,
            "highIndicators": counts.get(RiskLevel.HIGH, 0) + counts.get(RiskLevel.CRITICAL, 0),
            "criticalAlerts": critical_alerts,
        },
        "riskDistribution": _risk_distribution_dto(counts),
    }


@router.post("/personnel", status_code=status.HTTP_201_CREATED)
async def create_admin_personnel(
    body: AdminPersonnelCreate,
    request: Request,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    service_number = body.serviceNumber.upper()
    if db.query(User).filter(func.lower(User.email) == body.email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    if (
        db.query(Personnel)
        .filter(func.lower(Personnel.service_number) == service_number.lower())
        .first()
    ):
        raise HTTPException(status_code=409, detail="This service number is already registered")

    names = body.fullName.split(" ", 1)
    user = User(
        email=body.email,
        full_name=body.fullName,
        hashed_password=hash_password(body.initialPassword),
        role=UserRole.PERSONNEL,
        is_active=True,
        onboarding_complete=True,
    )
    db.add(user)
    db.flush()

    person = Personnel(
        user_id=user.id,
        service_number=service_number,
        first_name=names[0],
        last_name=names[1] if len(names) > 1 else "Personnel",
        rank=body.rank,
        unit=body.unit,
        status=PersonnelStatus.ACTIVE,
        risk_level=RiskLevel.LOW,
        risk_score=0,
    )
    db.add(person)
    db.flush()
    db.add(AuditLog(
        user_id=current_user.id,
        action="ADMIN_PERSONNEL_CREATED",
        resource_type="personnel",
        resource_id=person.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        details=json.dumps({
            "email": body.email,
            "serviceNumber": service_number,
            "unit": body.unit,
        }),
    ))

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Email or service number already exists",
        ) from error

    db.refresh(person)
    return _personnel_row_dto(person)


@router.get("/personnel")
async def get_admin_personnel(
    q: str | None = Query(None),
    unit: str | None = Query(None),
    level: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, alias="pageSize", ge=1, le=100),
    current_user: User = Depends(require_role(UserRole.SUPERVISOR)),
    db: Session = Depends(get_db),
):
    query = db.query(Personnel).options(joinedload(Personnel.user))

    if q:
        search = f"%{q.strip()}%"
        full_name = Personnel.first_name + " " + Personnel.last_name
        query = query.filter(
            or_(
                Personnel.first_name.ilike(search),
                Personnel.last_name.ilike(search),
                full_name.ilike(search),
                Personnel.service_number.ilike(search),
                Personnel.rank.ilike(search),
            )
        )
    if unit:
        query = query.filter(Personnel.unit == unit)
    if level:
        normalized_level = level.upper()
        if normalized_level in RiskLevel._value2member_map_:
            query = query.filter(Personnel.risk_level == RiskLevel(normalized_level))
        elif normalized_level in ("NORMAL", "ELEVATED"):
            query = query.filter(Personnel.id.is_(None))
        else:
            raise HTTPException(status_code=422, detail=f"Unsupported wellbeing level: {level}")

    total = query.count()
    pages = max(1, math.ceil(total / page_size))
    people = (
        query.order_by(Personnel.last_name.asc(), Personnel.first_name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    units = [
        row[0]
        for row in (
            db.query(Personnel.unit)
            .distinct()
            .order_by(Personnel.unit.asc())
            .all()
        )
    ]

    return {
        "rows": [_personnel_row_dto(person) for person in people],
        "total": total,
        "page": page,
        "pageSize": page_size,
        "pages": pages,
        "units": units,
    }


@router.get("/personnel/{personnel_id}")
async def get_admin_personnel_detail(
    personnel_id: str,
    request: Request,
    current_user: User = Depends(require_role(UserRole.SUPERVISOR)),
    db: Session = Depends(get_db),
):
    person = (
        db.query(Personnel)
        .options(joinedload(Personnel.user))
        .filter(Personnel.id == personnel_id)
        .first()
    )
    if not person:
        raise HTTPException(status_code=404, detail="Personnel not found")

    alert_items = (
        db.query(Alert)
        .options(joinedload(Alert.personnel), joinedload(Alert.assignee))
        .filter(Alert.personnel_id == personnel_id)
        .order_by(Alert.created_at.desc())
        .limit(100)
        .all()
    )

    support_requests = []
    if person.user_id:
        support_requests = (
            db.query(SupportRequest)
            .filter(SupportRequest.user_id == person.user_id)
            .order_by(SupportRequest.created_at.desc())
            .limit(100)
            .all()
        )

    visible = _clinical_visibility(current_user)

    assessments = []
    if visible["assessments"]:
        assessments = (
            db.query(Assessment)
            .options(joinedload(Assessment.assessor))
            .filter(Assessment.personnel_id == personnel_id)
            .order_by(Assessment.created_at.desc())
            .limit(100)
            .all()
        )

    journals = []
    if visible["journals"]:
        journals = (
            db.query(Journal)
            .filter(Journal.personnel_id == personnel_id)
            .order_by(Journal.created_at.desc())
            .limit(100)
            .all()
        )

    conversations = []
    if visible["conversations"] and person.user_id:
        conversations = (
            db.query(AIConversation)
            .options(selectinload(AIConversation.messages))
            .filter(AIConversation.user_id == person.user_id)
            .order_by(AIConversation.updated_at.desc())
            .limit(50)
            .all()
        )

    voice_entries = []
    if visible["voiceEntries"] and person.user_id:
        voice_entries = (
            db.query(VoiceEntry)
            .filter(VoiceEntry.user_id == person.user_id)
            .order_by(VoiceEntry.created_at.desc())
            .limit(100)
            .all()
        )

    show_raw_risk = _raw_risk_visible(current_user)
    risk_alerts = [
        alert
        for alert in reversed(alert_items)
        if alert.type in (
            AlertType.RISK_SCORE_CHANGE,
            AlertType.AI_FLAGGED,
            AlertType.BEHAVIORAL,
        )
    ][-30:]
    risk_trend = [
        {
            "date": alert.created_at,
            "level": _risk_level_for_alert(alert.severity).value,
            "score": None,
            "source": "ALERT",
        }
        for alert in risk_alerts
    ]
    risk_trend.append({
        "date": person.updated_at,
        "level": person.risk_level.value,
        "score": person.risk_score if show_raw_risk else None,
        "source": "CURRENT",
    })

    request_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    db.add(AuditLog(
        user_id=current_user.id,
        action="ADMIN_PERSONNEL_DETAIL_VIEW",
        resource_type="personnel",
        resource_id=person.id,
        ip_address=request_ip,
        user_agent=user_agent,
        details=json.dumps({"clinicalVisibility": visible}),
    ))
    for section, is_visible in visible.items():
        if is_visible:
            resource = CLINICAL_RESOURCES[section]
            db.add(AuditLog(
                user_id=current_user.id,
                action=f"ACCESS_GRANTED:{resource}:read",
                resource_type=resource,
                resource_id=person.id,
                ip_address=request_ip,
                user_agent=user_agent,
            ))
    db.commit()

    factors = []
    if show_raw_risk and person.risk_factors:
        factors = [item.strip() for item in person.risk_factors.split(",") if item.strip()]

    return {
        "profile": {
            "id": person.id,
            "name": person.full_name,
            "serviceNumber": person.service_number,
            "unit": person.unit,
            "rank": person.rank,
            "role": "USER",
            "status": _personnel_status(person),
            "createdAt": person.created_at,
            "lastLoginAt": None,
            "lastActiveAt": person.last_check_in or (person.user.updated_at if person.user else person.updated_at),
            "onboardingComplete": person.user.onboarding_complete if person.user else True,
        },
        "latestRisk": {
            "level": person.risk_level.value,
            "score": person.risk_score if show_raw_risk else None,
            "source": "current_operational_profile",
            "createdAt": person.updated_at,
        },
        "riskTrend": [
            {
                "level": item["level"],
                "source": item["source"].lower(),
                "createdAt": item["date"],
            }
            for item in risk_trend
        ],
        "alerts": [
            {
                "id": alert.id,
                "severity": _ui_alert_severity(alert.severity),
                "status": _ui_alert_status(alert.status),
                "reason": alert.description or alert.title,
                "source": alert.type.value.lower(),
                "createdAt": alert.created_at,
                "resolvedAt": alert.resolved_at,
            }
            for alert in alert_items
        ],
        "supportRequests": [
            {
                "id": item.id,
                "type": item.type,
                "message": item.message,
                "status": _support_status(item.status.value),
                "createdAt": item.created_at,
            }
            for item in support_requests
        ],
        "assessments": [
            {
                "id": item.id,
                "completedAt": item.created_at,
                "level": _score_level(item.score, item.max_score),
                "normalizedScore": 0.0 if item.max_score <= 0 else (item.score / item.max_score) * 100,
            }
            for item in assessments
        ],
        "journals": [
            {
                "id": item.id,
                "mood": item.mood,
                "content": item.content,
                "status": item.status,
                "wellbeingLevel": item.sentiment_label
                if item.sentiment_label in UI_RISK_LEVELS
                else None,
                "createdAt": item.created_at,
            }
            for item in journals
        ],
        "conversations": [
            {
                "id": conversation.id,
                "title": conversation.title,
                "createdAt": conversation.created_at,
                "messages": [
                    {
                        "role": message.role,
                        "content": message.content,
                        "riskFlag": message.risk_flag,
                        "createdAt": message.created_at,
                    }
                    for message in conversation.messages
                ],
            }
            for conversation in conversations
        ],
        "voiceEntries": [
            {
                "id": item.id,
                "durationSec": 0,
                "transcript": item.transcript,
                "wellbeingLevel": None,
                "createdAt": item.created_at,
            }
            for item in voice_entries
        ],
        "visible": {
            "risk": True,
            "assessments": visible["assessments"],
            "journals": visible["journals"],
            "conversations": visible["conversations"],
        },
    }


@router.get("/risk")
async def get_admin_risk(
    days: int = Query(30, ge=1, le=365),
    unit: str | None = Query(None),
    level: str | None = Query(None),
    current_user: User = Depends(require_role(UserRole.SUPERVISOR)),
    db: Session = Depends(get_db),
):
    personnel_query = db.query(Personnel)
    if unit:
        personnel_query = personnel_query.filter(Personnel.unit == unit)
    level_enum = None
    if level:
        normalized_level = level.upper()
        if normalized_level in RiskLevel._value2member_map_:
            level_enum = RiskLevel(normalized_level)
            personnel_query = personnel_query.filter(Personnel.risk_level == level_enum)
        elif normalized_level in ("NORMAL", "ELEVATED"):
            personnel_query = personnel_query.filter(Personnel.id.is_(None))
        else:
            raise HTTPException(status_code=422, detail=f"Unsupported wellbeing level: {level}")
    distribution = _risk_distribution_dto(_risk_counts(personnel_query))

    start_date = datetime.now(timezone.utc).date() - timedelta(days=days - 1)
    start = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    alert_query = (
        db.query(Alert)
        .options(joinedload(Alert.personnel), joinedload(Alert.assignee))
        .join(Personnel, Alert.personnel_id == Personnel.id)
        .filter(Alert.created_at >= start)
    )
    if unit:
        alert_query = alert_query.filter(Personnel.unit == unit)
    if level:
        if level_enum is None:
            alert_query = alert_query.filter(Alert.id.is_(None))
        else:
            severity = (
                AlertSeverity.MEDIUM
                if level_enum == RiskLevel.MODERATE
                else AlertSeverity(level_enum.value)
            )
            alert_query = alert_query.filter(Alert.severity == severity)

    alerts = alert_query.order_by(Alert.created_at.desc()).all()
    trend_by_date = {
        start_date + timedelta(days=index): {risk_level.value.lower(): 0 for risk_level in RISK_LEVELS}
        for index in range(days)
    }
    for alert in alerts:
        alert_date = alert.created_at.date()
        if alert_date in trend_by_date:
            risk_level = _risk_level_for_alert(alert.severity)
            trend_by_date[alert_date][risk_level.value.lower()] += 1

    trend = []
    for day, values in trend_by_date.items():
        trend.append({
            "date": day.isoformat(),
            "count": sum(values.values()),
        })

    return {
        "distribution": distribution,
        "trend": trend,
        "recentAlerts": [_alert_to_dto(alert) for alert in alerts[:20]],
    }


@router.get("/alerts")
async def get_admin_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, alias="pageSize", ge=1, le=100),
    alert_status: str | None = Query(None, alias="status"),
    severity: str | None = Query(None),
    current_user: User = Depends(require_role(UserRole.SUPERVISOR)),
    db: Session = Depends(get_db),
):
    query = db.query(Alert)
    if alert_status:
        query = query.filter(Alert.status.in_(_parse_alert_status(alert_status)))
    if severity:
        query = query.filter(Alert.severity == _parse_alert_severity(severity))

    total = query.count()
    pages = max(1, math.ceil(total / page_size))
    alerts = (
        query.options(joinedload(Alert.personnel), joinedload(Alert.assignee))
        .order_by(Alert.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "alerts": [_alert_to_dto(alert) for alert in alerts],
        "total": total,
        "page": page,
        "pageSize": page_size,
        "pages": pages,
    }


@router.put("/alerts/{alert_id}")
async def update_admin_alert(
    alert_id: str,
    body: AdminAlertUpdate,
    request: Request,
    current_user: User = Depends(require_role(UserRole.SUPERVISOR)),
    db: Session = Depends(get_db),
):
    if not body.model_fields_set:
        raise HTTPException(status_code=400, detail="No alert changes supplied")

    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    changes = {}
    if "assignedToId" in body.model_fields_set:
        if body.assignedToId:
            assignee = db.query(User).filter(User.id == body.assignedToId).first()
            if not assignee:
                raise HTTPException(status_code=404, detail="Assignee user not found")
        changes["assignedToId"] = {
            "from": alert.assigned_to,
            "to": body.assignedToId,
        }
        alert.assigned_to = body.assignedToId
        if body.assignedToId and alert.status in (
            AlertStatus.OPEN,
            AlertStatus.ACKNOWLEDGED,
        ):
            alert.status = AlertStatus.ASSIGNED

    if "status" in body.model_fields_set:
        if body.status is None:
            raise HTTPException(status_code=422, detail="Alert status cannot be null")
        new_status = _parse_update_status(body.status)
        changes["status"] = {
            "from": alert.status.value,
            "to": new_status.value,
        }
        alert.status = new_status
        if new_status == AlertStatus.RESOLVED:
            alert.resolved_at = datetime.now(timezone.utc)
        elif new_status not in (AlertStatus.DISMISSED,):
            alert.resolved_at = None

    db.add(AuditLog(
        user_id=current_user.id,
        action="ADMIN_ALERT_UPDATED",
        resource_type="alert",
        resource_id=alert.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        details=json.dumps(changes),
    ))
    db.commit()

    updated_alert = (
        db.query(Alert)
        .options(joinedload(Alert.personnel), joinedload(Alert.assignee))
        .filter(Alert.id == alert_id)
        .first()
    )
    if not updated_alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _alert_to_dto(updated_alert)


@router.get("/analytics")
async def get_admin_analytics(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    risk_distribution = _risk_distribution_dto(_risk_counts(db.query(Personnel)))

    unit_rows = (
        db.query(
            Personnel.unit,
            Personnel.risk_level,
            func.count(Personnel.id),
        )
        .group_by(Personnel.unit, Personnel.risk_level)
        .order_by(Personnel.unit.asc())
        .all()
    )
    units_by_name = {}
    for unit_name, risk_level, count in unit_rows:
        if unit_name not in units_by_name:
            units_by_name[unit_name] = {
                "unit": unit_name,
                "total": 0,
                "elevated": 0,
            }
        units_by_name[unit_name]["total"] += count
        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            units_by_name[unit_name]["elevated"] += count

    today = datetime.now(timezone.utc).date()
    first_day = today - timedelta(days=13)
    start = datetime.combine(first_day, datetime.min.time(), tzinfo=timezone.utc)
    activity = {
        first_day + timedelta(days=index): {
            "journals": 0,
            "assessments": 0,
            "voice": 0,
            "chats": 0,
        }
        for index in range(14)
    }

    activity_sources = (
        ("journals", db.query(Journal.created_at).filter(Journal.created_at >= start).all()),
        ("assessments", db.query(Assessment.created_at).filter(Assessment.created_at >= start).all()),
        ("voice", db.query(VoiceEntry.created_at).filter(VoiceEntry.created_at >= start).all()),
        (
            "chats",
            db.query(AIMessage.created_at)
            .filter(AIMessage.created_at >= start, AIMessage.role == "user")
            .all(),
        ),
    )
    for key, rows in activity_sources:
        for (created_at,) in rows:
            day = created_at.date()
            if day in activity:
                activity[day][key] += 1

    return {
        "riskDistribution": risk_distribution,
        "units": list(units_by_name.values()),
        "activity": [
            {
                "date": day.isoformat(),
                **counts,
            }
            for day, counts in activity.items()
        ],
    }


@router.get("/audit-logs")
async def get_admin_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, alias="pageSize", ge=1, le=200),
    action: str | None = Query(None),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    total = query.count()
    pages = max(1, math.ceil(total / page_size))
    logs = (
        query.options(joinedload(AuditLog.user))
        .order_by(AuditLog.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "logs": [
            {
                "id": log.id,
                "actorId": log.user_id,
                "actorName": log.user.full_name if log.user else "System",
                "action": log.action,
                "targetType": log.resource_type,
                "targetId": log.resource_id,
                "metadata": _safe_audit_metadata(log.details),
                "createdAt": log.timestamp,
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "pageSize": page_size,
        "pages": pages,
    }


@router.get("/monitoring/demo")
async def get_monitoring_demo(
    current_user: User = Depends(require_role(UserRole.SUPERVISOR)),
):
    """Return deterministic synthetic UI fixtures; no monitoring data is collected."""
    return {
        "demo": True,
        "generatedAt": datetime.now(timezone.utc),
        "cameras": [
            {
                "id": "demo-camera-01",
                "label": "Synthetic Perimeter View",
                "location": "Demo Sector A",
                "status": "DEMO_ONLY",
                "lastFrameAt": None,
                "activity": "No feed connected",
                "privacy": "SYNTHETIC_DATA_NO_CAPTURE",
            },
            {
                "id": "demo-camera-02",
                "label": "Synthetic Common Area View",
                "location": "Demo Sector B",
                "status": "DEMO_ONLY",
                "lastFrameAt": None,
                "activity": "No feed connected",
                "privacy": "SYNTHETIC_DATA_NO_CAPTURE",
            },
        ],
        "sleep": [
            {
                "personId": "demo-person-01",
                "name": "Demo Person A",
                "unit": "Synthetic Unit One",
                "restWindow": "22:00-06:00",
                "estimatedHours": 6.8,
                "interruptions": 1,
                "trend": "STABLE",
            },
            {
                "personId": "demo-person-02",
                "name": "Demo Person B",
                "unit": "Synthetic Unit Two",
                "restWindow": "23:30-05:30",
                "estimatedHours": 5.4,
                "interruptions": 2,
                "trend": "DECLINING",
            },
        ],
        "voice": [
            {
                "personId": "demo-person-01",
                "name": "Demo Person A",
                "sessionAt": "2025-01-15T09:00:00Z",
                "voiceCracks": 1,
                "longPauses": 2,
                "pitchVariance": 0.18,
                "confidence": 0.72,
                "note": "Synthetic demonstration metric; no audio was processed.",
            }
        ],
        "typing": [
            {
                "personId": "demo-person-02",
                "name": "Demo Person B",
                "sessionAt": "2025-01-15T09:15:00Z",
                "pauseCount": 4,
                "stuckOn": "Synthetic check-in prompt",
                "correctionRate": 0.08,
                "wpm": 34,
            }
        ],
        "habits": [
            {"label": "Demo check-in completion", "value": "82%", "change": "+3%", "status": "STABLE"},
            {"label": "Demo rest consistency", "value": "71%", "change": "-2%", "status": "WATCH"},
            {"label": "Demo support engagement", "value": "64%", "change": "+5%", "status": "IMPROVING"},
        ],
    }
