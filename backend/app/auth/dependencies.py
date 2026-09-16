"""
FastAPI dependencies for authentication and authorization.
"""
import json
from functools import wraps
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.audit_log import AuditLog
from app.auth.security import decode_access_token

security_scheme = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_scheme)],
    db: Session = Depends(get_db),
) -> User:
    """Extract and validate the current user from the JWT token."""
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_role(minimum_role: UserRole):
    """
    Dependency factory: require user to have at least the given role level.
    Returns 403 with a clear message (not empty data).
    """
    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not current_user.has_minimum_role(minimum_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "You do not have permission to access this resource",
                    "code": "INSUFFICIENT_ROLE",
                    "required_role": minimum_role.value,
                    "your_role": current_user.role.value,
                },
            )
        return current_user

    return role_checker


def require_permission(resource: str, action: str):
    """
    Dependency factory: require explicit permission grant.
    Clinical content (journals, assessments, etc.) uses this.
    ADMIN does NOT automatically get clinical permissions.
    """
    async def permission_checker(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        from app.auth.security import check_permission

        if not check_permission(current_user, resource, action):
            # Audit the denied access attempt
            audit = AuditLog(
                user_id=current_user.id,
                action=f"ACCESS_DENIED:{resource}:{action}",
                resource_type=resource,
                ip_address=request.client.host if request.client else None,
                details=json.dumps({
                    "reason": "Missing explicit permission",
                    "user_role": current_user.role.value,
                }),
            )
            db.add(audit)
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "You do not have permission to view this information",
                    "code": "MISSING_PERMISSION",
                    "resource": resource,
                    "action": action,
                },
            )

        # Audit successful access to sensitive content
        audit = AuditLog(
            user_id=current_user.id,
            action=f"ACCESS_GRANTED:{resource}:{action}",
            resource_type=resource,
            ip_address=request.client.host if request.client else None,
        )
        db.add(audit)
        db.commit()

        return current_user

    return permission_checker


def audit_action(action: str, resource_type: str):
    """
    Dependency factory that logs an audit event for the current request.
    """
    async def auditor(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        audit = AuditLog(
            user_id=current_user.id,
            action=action,
            resource_type=resource_type,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        db.add(audit)
        db.commit()
        return current_user

    return auditor
