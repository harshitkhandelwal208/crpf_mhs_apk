"""
Auth router - login, refresh token, logout.
Public endpoint for login; authenticated for refresh/logout.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit_log import AuditLog
from app.auth.security import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    rotate_refresh_token,
    revoke_all_user_tokens,
)
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.schemas.schemas import (
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    MessageResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Authenticate user and return JWT tokens."""
    user = authenticate_user(body.identifier, body.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user, db)

    # Audit login
    audit = AuditLog(
        user_id=user.id,
        action="LOGIN",
        resource_type="auth",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(audit)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Rotate refresh token and issue new access token."""
    result = rotate_refresh_token(body.refresh_token, db)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    new_refresh_token, user = result
    access_token = create_access_token(user)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke all refresh tokens for the current user (logout everywhere)."""
    revoke_all_user_tokens(current_user.id, db)

    # Audit logout
    audit = AuditLog(
        user_id=current_user.id,
        action="LOGOUT",
        resource_type="auth",
        ip_address=request.client.host if request.client else None,
    )
    db.add(audit)
    db.commit()

    return MessageResponse(message="Successfully logged out")
