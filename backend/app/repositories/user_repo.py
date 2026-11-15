from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import RefreshToken, User


async def get_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(User.email == email))


async def add(session: AsyncSession, user: User) -> User:
    session.add(user)
    await session.flush()
    return user


async def add_refresh_token(session: AsyncSession, token: RefreshToken) -> None:
    session.add(token)
    await session.flush()


async def get_refresh_token(session: AsyncSession, token_hash: str) -> RefreshToken | None:
    return await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
    )


async def revoke_all_refresh_tokens(session: AsyncSession, user_id: int, now: datetime) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
