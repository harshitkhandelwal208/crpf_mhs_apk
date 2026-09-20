"""
Journals router - personnel journal logging and clinical review
Supports both Android app personnel submissions and permission-gated clinical views.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user, require_permission
from app.models.user import User
from app.models.personnel import Personnel, PersonnelStatus, RiskLevel
from app.models.journal import Journal
from app.models.audit_log import AuditLog
from app.models.sync_receipt import SyncReceipt
from app.schemas.schemas import (
    JournalCreateRequest,
    JournalMobileResponse,
    JournalItem,
    JournalResponse,
    JournalListResponse,
)
from app.ai.providers import get_ai_provider
from app.services.risk_engine import record_signal

router = APIRouter(tags=["Journals"])


@router.post("/journals", response_model=JournalMobileResponse, status_code=status.HTTP_201_CREATED)
async def create_journal(
    body: JournalCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submits a private personnel journal entry from Android APK or Web.
    Analyzes sentiment and welfare indicators with the HK AI engine.
    """
    # Mobile workers retry after network interruption. A persisted receipt lets the
    # same client request return its original journal instead of creating duplicates.
    if body.client_request_id:
        receipt = db.scalar(
            select(SyncReceipt).where(
                SyncReceipt.user_id == current_user.id,
                SyncReceipt.resource_type == "journal",
                SyncReceipt.client_request_id == body.client_request_id,
            )
        )
        if receipt:
            existing = db.get(Journal, receipt.resource_id)
            if existing:
                return JournalMobileResponse(
                    journal=JournalItem(
                        id=existing.id,
                        mood=existing.mood,
                        content=existing.content,
                        status=existing.status,
                        created_at=existing.created_at.isoformat(),
                    )
                )

    # Ensure a linked personnel record exists for the user
    personnel = db.scalar(select(Personnel).where(Personnel.user_id == current_user.id))
    if not personnel:
        # Auto-create operational profile for newly authenticated personnel
        names = current_user.full_name.split(" ", 1)
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else "Officer"
        personnel = Personnel(
            user_id=current_user.id,
            service_number=f"CRPF-{current_user.id[:8].upper()}",
            first_name=first_name,
            last_name=last_name,
            rank="Personnel",
            unit="General Duty",
            status=PersonnelStatus.ACTIVE,
            risk_level=RiskLevel.LOW,
        )
        db.add(personnel)
        db.flush()

    # Analyze with AI Engine
    analysis = None
    is_flagged = False
    sentiment_label = "NEUTRAL"
    sentiment_score = 0.5

    if body.status == "SUBMITTED":
        provider = get_ai_provider()
        analysis = provider.analyze_journal(body.content)
        sentiment_label = analysis.wellbeing_signal
        sentiment_score = analysis.confidence
        is_flagged = analysis.requires_human_review

        # Escalate to risk engine if elevated/high distress
        if analysis.wellbeing_signal in ("HIGH", "CRITICAL", "ELEVATED"):
            record_signal(
                db,
                user_id=current_user.id,
                source="journal",
                level=analysis.wellbeing_signal,
                confidence=analysis.confidence,
                signals=analysis.signals,
                reason="AI analysis flagged distress in daily journal submission",
            )

    journal = Journal(
        personnel_id=personnel.id,
        title=body.title or "Daily Journal",
        content=body.content,
        mood=body.mood,
        status=body.status,
        sentiment_score=sentiment_score,
        sentiment_label=sentiment_label,
        is_flagged=is_flagged,
    )
    db.add(journal)
    db.flush()

    if body.client_request_id:
        db.add(SyncReceipt(
            user_id=current_user.id,
            resource_type="journal",
            client_request_id=body.client_request_id,
            resource_id=journal.id,
        ))

    # Update personnel last check in
    personnel.last_check_in = datetime.now(timezone.utc)

    # Audit logging
    audit = AuditLog(
        user_id=current_user.id,
        action="JOURNAL_SUBMITTED" if body.status == "SUBMITTED" else "JOURNAL_DRAFT_SAVED",
        resource_type="journal",
        resource_id=journal.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(audit)
    db.commit()
    db.refresh(journal)

    return JournalMobileResponse(
        journal=JournalItem(
            id=journal.id,
            mood=journal.mood,
            content=journal.content,
            status=journal.status,
            created_at=journal.created_at.isoformat(),
        )
    )


@router.get("/journals")
async def list_my_journals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List authenticated personnel's own journal reflections."""
    personnel = db.scalar(select(Personnel).where(Personnel.user_id == current_user.id))
    if not personnel:
        return {"journals": []}

    journals = db.scalars(
        select(Journal)
        .where(Journal.personnel_id == personnel.id)
        .order_by(Journal.created_at.desc())
    ).all()

    return {
        "journals": [
            {
                "id": j.id,
                "mood": j.mood,
                "content": j.content,
                "status": j.status,
                "created_at": j.created_at.isoformat(),
            }
            for j in journals
        ]
    }


# ── Permission-Gated Clinical Endpoint for Medical / MHP Staff ──

@router.get(
    "/personnel/{personnel_id}/journals",
    response_model=JournalListResponse,
    dependencies=[Depends(require_permission("clinical:journals", "read"))],
)
async def get_personnel_journals(
    personnel_id: str,
    db: Session = Depends(get_db),
):
    """
    Get journals for a personnel member.
    Requires explicit 'clinical:journals:read' permission.
    ADMIN role alone is NOT sufficient.
    All access is audited by the require_permission dependency.
    """
    personnel = db.query(Personnel).filter(Personnel.id == personnel_id).first()
    if not personnel:
        raise HTTPException(status_code=404, detail="Personnel not found")

    journals = (
        db.query(Journal)
        .filter(Journal.personnel_id == personnel_id)
        .order_by(Journal.created_at.desc())
        .all()
    )

    return JournalListResponse(
        items=[JournalResponse.model_validate(journal) for journal in journals],
        total=len(journals),
    )
