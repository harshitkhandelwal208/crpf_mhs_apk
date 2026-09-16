"""
Audit logs router - searchable, filterable audit log viewer.
ADMIN+ access only. Never exposes raw secrets.
"""
import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.audit_log import AuditLog
from app.auth.dependencies import require_role
from app.schemas.schemas import AuditLogResponse, AuditLogListResponse

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: str | None = Query(None, description="Filter by action type"),
    resource_type: str | None = Query(None),
    user_id: str | None = Query(None),
    search: str | None = Query(None, description="Search in action or details"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """List audit logs with pagination and filters. Never exposes raw secrets."""
    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (AuditLog.action.ilike(search_term))
            | (AuditLog.details.ilike(search_term))
        )

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    if sort_order == "desc":
        query = query.order_by(AuditLog.timestamp.desc())
    else:
        query = query.order_by(AuditLog.timestamp.asc())

    offset = (page - 1) * page_size
    logs = query.offset(offset).limit(page_size).all()

    items = []
    for log in logs:
        user = None
        if log.user_id:
            user = db.query(User).filter(User.id == log.user_id).first()

        # Sanitize details - never expose raw tokens or secrets
        sanitized_details = log.details
        if sanitized_details:
            for secret_key in ["password", "token", "secret", "key"]:
                if secret_key in sanitized_details.lower():
                    sanitized_details = "[REDACTED - contains sensitive data]"
                    break

        items.append(AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            user_email=user.email if user else None,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            ip_address=log.ip_address,
            details=sanitized_details,
            timestamp=log.timestamp,
        ))

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
