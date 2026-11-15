from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.profile import Profile
from app.models.user import User
from app.repositories import profile_repo
from app.schemas.profile import ProfileIn, ProfileOut


async def get(session: AsyncSession, user: User) -> ProfileOut:
    profile = await profile_repo.get(session, user.id)
    if profile is None:
        raise NotFoundError("Profile not set up yet.", code="profile_missing")
    return ProfileOut.model_validate(profile)


async def save(session: AsyncSession, user: User, data: ProfileIn) -> ProfileOut:
    """Create the profile (end of onboarding) or replace it (edit)."""
    values = data.model_dump(mode="json")
    profile = await profile_repo.get(session, user.id)
    if profile is None:
        profile = await profile_repo.add(session, Profile(user_id=user.id, **values))
    else:
        for key, value in values.items():
            setattr(profile, key, value)
    await session.commit()
    await session.refresh(profile)
    return ProfileOut.model_validate(profile)
