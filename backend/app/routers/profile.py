from fastapi import APIRouter

from app.core.deps import CurrentUser, SessionDep
from app.schemas.common import ErrorOut
from app.schemas.profile import ProfileIn, ProfileOut
from app.services import profile_service

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileOut, responses={404: {"model": ErrorOut}})
async def get_profile(user: CurrentUser, session: SessionDep) -> ProfileOut:
    return await profile_service.get(session, user)


@router.put("", response_model=ProfileOut, summary="Create or replace the profile")
async def save_profile(data: ProfileIn, user: CurrentUser, session: SessionDep) -> ProfileOut:
    return await profile_service.save(session, user, data)
