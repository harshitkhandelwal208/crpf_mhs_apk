"""
Support Router - Support requests, emergency contacts, and wellbeing resources
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.support import SupportRequest, SupportStatus, EmergencyContact, Resource
from app.models.audit_log import AuditLog
from app.schemas.schemas import (
    SupportRequestInput,
    SupportResponse,
    SupportRequestItem,
    EmergencyContactResponse,
    ResourceResponse,
)
from app.services.risk_engine import record_signal

router = APIRouter(tags=["Support & Resources"])


@router.post("/support/request", response_model=SupportResponse, status_code=status.HTTP_201_CREATED)
async def create_support_request(
    body: SupportRequestInput,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submits a confidential support request from Android or Web.
    Urgent requests trigger automated alerts for welfare officers.
    """
    item = SupportRequest(
        user_id=current_user.id,
        type=body.type,
        message=body.message,
        status=SupportStatus.PENDING,
    )
    db.add(item)
    db.flush()

    if body.type.lower() in ("urgent", "crisis"):
        record_signal(
            db,
            user_id=current_user.id,
            source="support_request",
            level="ELEVATED",
            confidence=1.0,
            signals=["urgent_support_request"],
            reason=f"Urgent support request submitted: {body.message[:100]}",
        )

    audit = AuditLog(
        user_id=current_user.id,
        action="SUPPORT_REQUEST_CREATED",
        resource_type="support_request",
        resource_id=item.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(audit)
    db.commit()
    db.refresh(item)

    return SupportResponse(id=item.id, status=item.status.value)


@router.get("/support/requests", response_model=list[SupportRequestItem])
async def list_support_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List authenticated user's support requests."""
    items = db.scalars(
        select(SupportRequest)
        .where(SupportRequest.user_id == current_user.id)
        .order_by(SupportRequest.created_at.desc())
    ).all()
    return items


@router.get("/emergency-contacts", response_model=list[EmergencyContactResponse])
async def list_emergency_contacts(db: Session = Depends(get_db)):
    """List active emergency and military crisis support contacts."""
    contacts = db.scalars(
        select(EmergencyContact)
        .where(EmergencyContact.active.is_(True))
        .order_by(EmergencyContact.sort_order.asc())
    ).all()
    return contacts


@router.get("/resources", response_model=list[ResourceResponse])
async def list_resources(
    category: str | None = None,
    db: Session = Depends(get_db),
):
    """List categorized wellbeing self-help resources."""
    stmt = select(Resource).where(Resource.active.is_(True))
    if category:
        stmt = stmt.where(Resource.category == category)
    stmt = stmt.order_by(Resource.category.asc(), Resource.title.asc())
    resources = db.scalars(stmt).all()
    return resources

