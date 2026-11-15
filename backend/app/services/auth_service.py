"""Accounts: register, login, refresh rotation, logout, change password."""

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError, AuthError, ConflictError
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    password_needs_rehash,
    utcnow,
    verify_password,
)
from app.models.user import RefreshToken, User
from app.repositories import profile_repo, user_repo
from app.schemas.auth import ChangePasswordIn, LoginIn, RegisterIn, TokenOut, UserOut

INVALID_LOGIN = "Email or password is wrong."


@dataclass
class AuthResult:
    token: TokenOut
    refresh_token: str


async def user_out(session: AsyncSession, user: User) -> UserOut:
    has_profile = await profile_repo.get(session, user.id) is not None
    return UserOut(
        id=user.id,
        email=user.email,
        is_admin=user.is_admin,
        created_at=user.created_at,
        has_profile=has_profile,
    )


async def _issue(session: AsyncSession, user: User) -> AuthResult:
    raw = new_refresh_token()
    await user_repo.add_refresh_token(
        session,
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw),
            expires_at=utcnow() + timedelta(days=get_settings().refresh_token_days),
        ),
    )
    access, lifetime = create_access_token(user.id)
    token = TokenOut(access_token=access, expires_in=lifetime, user=await user_out(session, user))
    return AuthResult(token=token, refresh_token=raw)


async def register(session: AsyncSession, data: RegisterIn) -> AuthResult:
    if await user_repo.get_by_email(session, data.email):
        raise ConflictError("An account with this email already exists.", code="email_taken")
    now = utcnow()
    user = await user_repo.add(
        session,
        User(
            email=data.email,
            password_hash=hash_password(data.password),
            consent_at=now,
            last_login_at=now,
        ),
    )
    await session.refresh(user)
    result = await _issue(session, user)
    await session.commit()
    return result


async def login(session: AsyncSession, data: LoginIn) -> AuthResult:
    user = await user_repo.get_by_email(session, data.email)
    if user is None:
        verify_password(DUMMY_PASSWORD_HASH, data.password)
        raise AuthError(INVALID_LOGIN, code="invalid_login")
    if not verify_password(user.password_hash, data.password):
        raise AuthError(INVALID_LOGIN, code="invalid_login")
    if not user.is_active:
        raise AuthError("This account is disabled. Contact the admin.", code="account_disabled")
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(data.password)
    user.last_login_at = utcnow()
    result = await _issue(session, user)
    await session.commit()
    return result


async def refresh(session: AsyncSession, raw_token: str | None) -> AuthResult:
    if not raw_token:
        raise AuthError("Not signed in.", code="no_refresh_token")
    now = utcnow()
    stored = await user_repo.get_refresh_token(session, hash_refresh_token(raw_token))
    if stored is None:
        raise AuthError("Session expired. Sign in again.", code="refresh_invalid")
    if stored.revoked_at is not None:
        # A rotated token was used again: treat as theft and end every session.
        await user_repo.revoke_all_refresh_tokens(session, stored.user_id, now)
        await session.commit()
        raise AuthError("Session expired. Sign in again.", code="refresh_reused")
    if stored.expires_at <= now:
        raise AuthError("Session expired. Sign in again.", code="refresh_expired")
    user = await user_repo.get_by_id(session, stored.user_id)
    if user is None or not user.is_active:
        raise AuthError("Session expired. Sign in again.", code="refresh_invalid")
    stored.revoked_at = now
    result = await _issue(session, user)
    await session.commit()
    return result


async def logout(session: AsyncSession, raw_token: str | None) -> None:
    if not raw_token:
        return
    stored = await user_repo.get_refresh_token(session, hash_refresh_token(raw_token))
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = utcnow()
        await session.commit()


async def change_password(session: AsyncSession, user: User, data: ChangePasswordIn) -> AuthResult:
    if not verify_password(user.password_hash, data.current_password):
        raise AppError("Current password is wrong.", code="wrong_password")
    user.password_hash = hash_password(data.new_password)
    # Sign out every other device; this one gets a fresh session.
    await user_repo.revoke_all_refresh_tokens(session, user.id, utcnow())
    result = await _issue(session, user)
    await session.commit()
    return result


async def me(session: AsyncSession, user: User) -> UserOut:
    return await user_out(session, user)


async def set_password(session: AsyncSession, email: str, new_password: str) -> bool:
    """Admin CLI: set a password and end all sessions. Returns False if no such user."""
    user = await user_repo.get_by_email(session, email.strip().lower())
    if user is None:
        return False
    user.password_hash = hash_password(new_password)
    await user_repo.revoke_all_refresh_tokens(session, user.id, utcnow())
    await session.commit()
    return True


async def set_admin(session: AsyncSession, email: str, is_admin: bool) -> bool:
    user = await user_repo.get_by_email(session, email.strip().lower())
    if user is None:
        return False
    user.is_admin = is_admin
    await session.commit()
    return True
