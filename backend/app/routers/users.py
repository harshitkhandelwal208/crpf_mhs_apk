"""
Users router - user profile and user management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.permission import Permission
from app.auth.dependencies import get_current_user, require_role
from app.auth.security import hash_password
from app.schemas.schemas import (
    UserResponse,
    UserCreateRequest,
    UserUpdateRequest,
    PermissionGrantRequest,
    PermissionResponse,
    MessageResponse,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Get the authenticated user's profile."""
    return current_user


@router.get("", response_model=list[UserResponse])
async def list_users(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """List all users (ADMIN+ only)."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return users


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    body: UserCreateRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Create a new user (ADMIN+ only)."""
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    # Only SUPER_ADMIN can create ADMIN or SUPER_ADMIN users
    if body.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Only SUPER_ADMIN can create admin-level users",
                    "code": "INSUFFICIENT_ROLE",
                },
            )

    user = User(
        email=body.email,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    body: UserUpdateRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Update a user (ADMIN+ only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.full_name is not None:
        user.full_name = body.full_name
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.role is not None:
        if body.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
            if current_user.role != UserRole.SUPER_ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "message": "Only SUPER_ADMIN can assign admin-level roles",
                        "code": "INSUFFICIENT_ROLE",
                    },
                )
        user.role = body.role

    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/permissions", response_model=PermissionResponse, status_code=201)
async def grant_permission(
    user_id: str,
    body: PermissionGrantRequest,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """Grant an explicit permission to a user (SUPER_ADMIN only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if permission already exists
    existing = (
        db.query(Permission)
        .filter(
            Permission.user_id == user_id,
            Permission.resource == body.resource,
            Permission.action == body.action,
        )
        .first()
    )
    if existing:
        existing.granted = True
        existing.granted_by = current_user.id
        db.commit()
        db.refresh(existing)
        return existing

    perm = Permission(
        user_id=user_id,
        resource=body.resource,
        action=body.action,
        granted=True,
        granted_by=current_user.id,
    )
    db.add(perm)
    db.commit()
    db.refresh(perm)
    return perm


@router.delete("/{user_id}/permissions/{permission_id}", response_model=MessageResponse)
async def revoke_permission(
    user_id: str,
    permission_id: str,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """Revoke a permission from a user (SUPER_ADMIN only)."""
    perm = (
        db.query(Permission)
        .filter(Permission.id == permission_id, Permission.user_id == user_id)
        .first()
    )
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")

    perm.granted = False
    db.commit()
    return MessageResponse(message="Permission revoked")
