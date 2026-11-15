from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, SessionDep
from app.schemas.common import ErrorOut
from app.schemas.history import HistoryDayOut, MonthOut
from app.services import history_service

router = APIRouter(prefix="/history", tags=["history"])

_errors = {400: {"model": ErrorOut}, 409: {"model": ErrorOut}}


@router.get(
    "/month",
    response_model=MonthOut,
    responses=_errors,
    summary="What was logged on each day of a month (default: this month)",
)
async def month(
    user: CurrentUser,
    session: SessionDep,
    month: Annotated[str | None, Query(description="YYYY-MM")] = None,
) -> MonthOut:
    return await history_service.month(session, user, month)


@router.get("/days/{day}", response_model=HistoryDayOut, responses=_errors)
async def day(day: date, user: CurrentUser, session: SessionDep) -> HistoryDayOut:
    return await history_service.day(session, user, day)
