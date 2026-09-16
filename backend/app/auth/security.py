"""
JWT token creation and verification, password hashing.
"""
import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User, UserRole
from app.models.refresh_token import RefreshToken
from app.models.permission import Permission

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _hash_token(token: str) -> str:
    """Hash a refresh token for storage (don't store raw tokens)."""
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(user: User) -> str:
    """Create a short-lived JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": user.id,
        "email": user.email,
        "role": user.role.value,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(user: User, db: Session) -> str:
    """Create a long-lived refresh token and store its hash."""
    raw_token = str(uuid.uuid4())
    token_hash = _hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    db_token = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(db_token)
    db.commit()

    return raw_token


def rotate_refresh_token(old_raw_token: str, db: Session) -> tuple[str, User] | None:
    """
    Rotate a refresh token: revoke the old one, issue a new one.
    Returns (new_raw_token, user) or None if invalid/revoked.
    """
    old_hash = _hash_token(old_raw_token)
    old_record = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == old_hash)
        .first()
    )

    if not old_record:
        return None

    if old_record.is_revoked:
        # Possible token reuse attack - revoke ALL user tokens
        db.query(RefreshToken).filter(
            RefreshToken.user_id == old_record.user_id
        ).update({"is_revoked": True})
        db.commit()
        return None

    if old_record.expires_at < datetime.now(timezone.utc):
        return None

    # Revoke old token
    old_record.is_revoked = True

    # Get the user
    user = db.query(User).filter(User.id == old_record.user_id).first()
    if not user or not user.is_active:
        db.commit()
        return None

    # Issue new token
    new_raw_token = create_refresh_token(user, db)
    old_record.replaced_by = _hash_token(new_raw_token)
    db.commit()

    return new_raw_token, user


def revoke_all_user_tokens(user_id: str, db: Session) -> None:
    """Revoke all refresh tokens for a user (logout everywhere)."""
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id
    ).update({"is_revoked": True})
    db.commit()


def decode_access_token(token: str) -> dict | None:
    """Decode and validate an access token."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def authenticate_user(email: str, password: str, db: Session) -> User | None:
    """Authenticate a user by email and password."""
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


def check_permission(user: User, resource: str, action: str) -> bool:
    """
    Check if a user has an explicit permission grant.
    This is separate from role checks — clinical content requires
    explicit grants even for ADMIN users.
    """
    for perm in user.permissions:
        if (
            perm.resource == resource
            and perm.action == action
            and perm.granted
        ):
            return True
    return False
