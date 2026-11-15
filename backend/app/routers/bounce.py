from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, SessionDep
from app.schemas.bounce import BouncePlanOut, BounceStatusOut, GymProfileIn, GymProfileOut
from app.schemas.common import ErrorOut
from app.services.bounce import service
from app.services.bounce.llm import LLMClient, get_llm

router = APIRouter(prefix="/bounce", tags=["bounce"])

LLMDep = Annotated[LLMClient | None, Depends(get_llm)]


@router.get(
    "/status",
    response_model=BounceStatusOut,
    responses={409: {"model": ErrorOut}},
    summary="Bounce's state, message and immediate suggestions for today",
)
async def bounce_status(user: CurrentUser, session: SessionDep, llm: LLMDep) -> BounceStatusOut:
    return await service.status(session, user, llm)


@router.get(
    "/plan",
    response_model=BouncePlanOut,
    responses={404: {"model": ErrorOut}},
    summary="The current weekly plan",
)
async def get_plan(user: CurrentUser, session: SessionDep) -> BouncePlanOut:
    return await service.current_plan(session, user)


@router.post(
    "/plan",
    response_model=BouncePlanOut,
    responses={
        409: {"model": ErrorOut, "description": "checkin_needed, gym_profile_needed, plan_current"},
        429: {"model": ErrorOut},
        502: {"model": ErrorOut, "description": "The AI service failed"},
        503: {"model": ErrorOut, "description": "bounce_disabled"},
    },
    summary="Ask Bounce for a new weekly plan. After a week it needs a newer check-in.",
)
async def create_plan(user: CurrentUser, session: SessionDep, llm: LLMDep) -> BouncePlanOut:
    return await service.generate(session, user, llm)


@router.get(
    "/gym-profile",
    response_model=GymProfileOut,
    responses={404: {"model": ErrorOut}},
    summary="Gym experience, schedule and supplements",
)
async def get_gym_profile(user: CurrentUser, session: SessionDep) -> GymProfileOut:
    return await service.get_gym_profile(session, user)


@router.put("/gym-profile", response_model=GymProfileOut, summary="Save gym details")
async def put_gym_profile(
    data: GymProfileIn, user: CurrentUser, session: SessionDep
) -> GymProfileOut:
    return await service.save_gym_profile(session, user, data)
