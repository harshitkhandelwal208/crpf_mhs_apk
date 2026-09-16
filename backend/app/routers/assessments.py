"""
Assessments router - clinical content requiring explicit permission.
ADMIN does NOT automatically get access. Access is audited.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.assessment import Assessment
from app.models.personnel import Personnel
from app.auth.dependencies import require_permission
from app.schemas.schemas import AssessmentResponse, AssessmentListResponse

router = APIRouter(prefix="/personnel", tags=["Assessments (Clinical)"])


@router.get(
    "/{personnel_id}/assessments",
    response_model=AssessmentListResponse,
    dependencies=[Depends(require_permission("clinical:assessments", "read"))],
)
async def get_personnel_assessments(
    personnel_id: str,
    db: Session = Depends(get_db),
):
    """
    Get assessments for a personnel member.
    Requires explicit 'clinical:assessments:read' permission.
    ADMIN role alone is NOT sufficient.
    All access is audited by the require_permission dependency.
    """
    personnel = db.query(Personnel).filter(Personnel.id == personnel_id).first()
    if not personnel:
        raise HTTPException(status_code=404, detail="Personnel not found")

    assessments = (
        db.query(Assessment)
        .filter(Assessment.personnel_id == personnel_id)
        .order_by(Assessment.created_at.desc())
        .all()
    )

    return AssessmentListResponse(items=assessments, total=len(assessments))
