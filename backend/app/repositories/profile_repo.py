from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile


async def get(session: AsyncSession, user_id: int) -> Profile | None:
    return await session.get(Profile, user_id)


async def add(session: AsyncSession, profile: Profile) -> Profile:
    session.add(profile)
    await session.flush()
    return profile
