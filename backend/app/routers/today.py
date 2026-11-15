from fastapi import APIRouter

from app.core.deps import CurrentUser, SessionDep
from app.schemas.common import ErrorOut
from app.schemas.today import TodayOut
from app.services import today_service

router = APIRouter(prefix="/today", tags=["today"])


@router.get("", response_model=TodayOut, responses={409: {"model": ErrorOut}})
async def get_today(user: CurrentUser, session: SessionDep) -> TodayOut:
    return await today_service.get_today(session, user)
