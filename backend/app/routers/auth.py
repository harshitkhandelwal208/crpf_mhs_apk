"""
Auth router - login, refresh token, logout.
Public endpoint for login; authenticated for refresh/logout.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.personnel import Personnel, PersonnelStatus, RiskLevel
from app.models.user import User, UserRole
from app.auth.security import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    hash_password,
    rotate_refresh_token,
    revoke_all_user_tokens,
)
from app.auth.dependencies import get_current_user
from app.schemas.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    RefreshRequest,
    MessageResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Public personnel registration for the Android mobile application.
    Creates a user account with role PERSONNEL and a linked personnel service record.
    """
    email_clean = str(body.email).strip().lower()
    service_no_clean = body.service_number.strip().upper()

    # 1. Ensure unique email and service number
    if db.query(User).filter(User.email == email_clean).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    if db.query(Personnel).filter(Personnel.service_number == service_no_clean).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A personnel record with this service number already exists",
        )

    # 2. Create user account
    full_name = f"{body.first_name.strip()} {body.last_name.strip()}"
    new_user = User(
        email=email_clean,
        full_name=full_name,
        hashed_password=hash_password(body.password),
        role=UserRole.PERSONNEL,
        is_active=True,
        onboarding_complete=True,
    )
    db.add(new_user)
    db.flush()

    # 3. Create linked personnel profile
    new_personnel = Personnel(
        user_id=new_user.id,
        service_number=service_no_clean,
        first_name=body.first_name.strip(),
        last_name=body.last_name.strip(),
        rank=body.rank.strip(),
        unit=body.unit.strip(),
        phone=body.phone.strip() if body.phone else None,
        status=PersonnelStatus.ACTIVE,
        risk_level=RiskLevel.LOW,
        risk_score=15.0,
    )
    db.add(new_personnel)

    # 4. Audit account creation
    audit = AuditLog(
        user_id=new_user.id,
        action="REGISTER",
        resource_type="auth",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        details=f"Registered service number {service_no_clean}, unit {body.unit.strip()}",
    )
    db.add(audit)
    db.commit()

    # 5. Return JWT token pair
    access_token = create_access_token(new_user)
    refresh_token = create_refresh_token(new_user, db)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


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
