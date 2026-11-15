from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError
from app.models.profile import Profile
from app.models.user import User
from app.repositories import profile_repo


async def require_profile(session: AsyncSession, user: User) -> Profile:
    """Most features need height, weight and timezone from the profile."""
    profile = await profile_repo.get(session, user.id)
    if profile is None:
        raise ConflictError("Finish setting up your profile first.", code="profile_missing")
    return profile
