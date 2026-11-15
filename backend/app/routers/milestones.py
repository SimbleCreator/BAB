from fastapi import APIRouter, status

from app.core.deps import CurrentUser, SessionDep
from app.schemas.milestone import MilestoneOut
from app.services import milestone_service

router = APIRouter(prefix="/milestones", tags=["milestones"])


@router.get("", response_model=list[MilestoneOut])
async def list_milestones(user: CurrentUser, session: SessionDep) -> list[MilestoneOut]:
    return await milestone_service.list_milestones(session, user)


@router.post(
    "/seen",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark every unlocked milestone as seen (after showing the celebration)",
)
async def mark_seen(user: CurrentUser, session: SessionDep) -> None:
    await milestone_service.mark_seen(session, user)
