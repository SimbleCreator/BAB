"""Password hashing, JWT access tokens and opaque refresh tokens."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings

_hasher = PasswordHasher()
_ALGORITHM = "HS256"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


# A real hash so login for an unknown email costs the same time as a wrong password.
DUMMY_PASSWORD_HASH = _hasher.hash(secrets.token_urlsafe(16))


def create_access_token(user_id: int) -> tuple[str, int]:
    """Return (token, lifetime in seconds)."""
    settings = get_settings()
    lifetime = settings.access_token_minutes * 60
    now = utcnow()
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(seconds=lifetime),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM), lifetime


def decode_access_token(token: str) -> int | None:
    """Return the user id, or None for any invalid or expired token."""
    try:
        payload = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=[_ALGORITHM],
            options={"require": ["sub", "exp", "type"]},
        )
    except jwt.PyJWTError:
        return None
    if payload.get("type") != "access":
        return None
    try:
        return int(payload["sub"])
    except (TypeError, ValueError):
        return None


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
