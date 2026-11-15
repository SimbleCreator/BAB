"""FastAPI dependencies shared by routers."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import AuthError, ForbiddenError
from app.core.security import decode_access_token
from app.models.user import User
from app.repositories import user_repo

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    session: SessionDep,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if creds is None:
        raise AuthError("Not signed in.")
    user_id = decode_access_token(creds.credentials)
    if user_id is None:
        raise AuthError("Session expired. Sign in again.", code="token_invalid")
    user = await user_repo.get_by_id(session, user_id)
    if user is None or not user.is_active:
        raise AuthError("Session expired. Sign in again.", code="token_invalid")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> User:
    if not user.is_admin:
        raise ForbiddenError("Admins only.")
    return user


AdminUser = Annotated[User, Depends(require_admin)]
