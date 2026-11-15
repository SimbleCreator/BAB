from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.timeutil import local_today
from app.models.profile import Profile
from app.models.user import User
from app.repositories import profile_repo
from app.schemas.profile import ProfileIn, ProfileOut
from app.services import nutrition_service, training_service


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
        # End of onboarding: create the first training plan for this week.
        profile = await profile_repo.add(session, Profile(user_id=user.id, **values))
        await training_service.ensure_plan(
            session, user, profile, training_service.week_start_for(local_today(profile.timezone))
        )
        await nutrition_service.set_targets_from_profile(
            session, user, profile, "Starting targets from your profile."
        )
    else:
        plan_changed = any(values[f] != getattr(profile, f) for f in training_service.PLAN_FIELDS)
        targets_changed = any(
            float(values[f]) != float(getattr(profile, f))
            if f in ("height_cm", "weight_kg")
            else values[f] != getattr(profile, f)
            for f in nutrition_service.TARGET_FIELDS
        )
        for key, value in values.items():
            setattr(profile, key, value)
        if plan_changed:
            await training_service.regenerate_from_tomorrow(session, user, profile)
        if targets_changed:
            await nutrition_service.set_targets_from_profile(
                session, user, profile, "Recalculated after a profile change."
            )
    await session.commit()
    await session.refresh(profile)
    return ProfileOut.model_validate(profile)
