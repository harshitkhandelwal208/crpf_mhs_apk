"""
Journals router - clinical content requiring explicit permission.
ADMIN does NOT automatically get access. Access is audited.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.journal import Journal
from app.models.personnel import Personnel
from app.auth.dependencies import require_permission
from app.schemas.schemas import JournalResponse, JournalListResponse

router = APIRouter(prefix="/personnel", tags=["Journals (Clinical)"])


@router.get(
    "/{personnel_id}/journals",
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

    return JournalListResponse(items=journals, total=len(journals))
