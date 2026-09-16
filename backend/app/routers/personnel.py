"""
Personnel router - paginated, filterable, sortable personnel list and profiles.
"""
import math
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.user import User, UserRole
from app.models.personnel import Personnel, PersonnelStatus, RiskLevel
from app.models.alert import Alert
from app.auth.dependencies import get_current_user, require_role
from app.schemas.schemas import (
    PersonnelResponse,
    PersonnelDetailResponse,
    PersonnelUpdateRequest,
    PersonnelListResponse,
)

router = APIRouter(prefix="/personnel", tags=["Personnel"])


@router.get("", response_model=PersonnelListResponse)
async def list_personnel(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None, description="Search by name or service number"),
    status: PersonnelStatus | None = Query(None),
    risk_level: RiskLevel | None = Query(None),
    unit: str | None = Query(None),
    sort_by: str = Query("last_name", description="Sort field"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: User = Depends(require_role(UserRole.SUPERVISOR)),
    db: Session = Depends(get_db),
):
    """List personnel with search, filters, sorting, and pagination."""
    query = db.query(Personnel)

    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Personnel.first_name.ilike(search_term))
            | (Personnel.last_name.ilike(search_term))
            | (Personnel.service_number.ilike(search_term))
        )

    if status:
        query = query.filter(Personnel.status == status)

    if risk_level:
        query = query.filter(Personnel.risk_level == risk_level)

    if unit:
        query = query.filter(Personnel.unit.ilike(f"%{unit}%"))

    # Total count before pagination
    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    # Apply sorting
    sort_column = getattr(Personnel, sort_by, Personnel.last_name)
    if sort_order == "desc":
        sort_column = sort_column.desc()
    query = query.order_by(sort_column)

    # Apply pagination
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

    return PersonnelListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{personnel_id}", response_model=PersonnelDetailResponse)
async def get_personnel(
    personnel_id: str,
    current_user: User = Depends(require_role(UserRole.SUPERVISOR)),
    db: Session = Depends(get_db),
):
    """Get detailed personnel profile. Risk score hidden from non-authorized roles."""
    person = db.query(Personnel).filter(Personnel.id == personnel_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Personnel not found")

    alert_count = db.query(func.count(Alert.id)).filter(
        Alert.personnel_id == personnel_id
    ).scalar()

    # Only MENTAL_HEALTH_PROFESSIONAL and SUPER_ADMIN see raw risk scores
    show_raw_score = current_user.role in (
        UserRole.MENTAL_HEALTH_PROFESSIONAL,
        UserRole.SUPER_ADMIN,
    )

    return PersonnelDetailResponse(
        id=person.id,
        service_number=person.service_number,
        first_name=person.first_name,
        last_name=person.last_name,
        rank=person.rank,
        unit=person.unit,
        status=person.status,
        risk_level=person.risk_level,
        risk_score=person.risk_score if show_raw_score else None,
        risk_factors=person.risk_factors if show_raw_score else None,
        phone=person.phone,
        notes=person.notes,
        last_check_in=person.last_check_in,
        alert_count=alert_count or 0,
        created_at=person.created_at,
    )


@router.put("/{personnel_id}", response_model=PersonnelResponse)
async def update_personnel(
    personnel_id: str,
    body: PersonnelUpdateRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Update personnel operational data (ADMIN+ only)."""
    person = db.query(Personnel).filter(Personnel.id == personnel_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Personnel not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(person, key, value)

    db.commit()
    db.refresh(person)
    return person
