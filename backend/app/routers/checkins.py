from datetime import date

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, SessionDep
from app.schemas.checkin import CheckinIn, CheckinOut, CheckinStatusOut
from app.schemas.common import ErrorOut
from app.services import checkin_service

router = APIRouter(prefix="/checkins", tags=["checkins"])

_errors = {400: {"model": ErrorOut}, 409: {"model": ErrorOut}}


@router.get("", response_model=list[CheckinOut], summary="All check-ins, newest first")
async def list_checkins(user: CurrentUser, session: SessionDep) -> list[CheckinOut]:
    return await checkin_service.list_checkins(session, user)


@router.get("/status", response_model=CheckinStatusOut, responses=_errors)
async def checkin_status(user: CurrentUser, session: SessionDep) -> CheckinStatusOut:
    return await checkin_service.status(session, user)


@router.put(
    "/{day}",
    response_model=CheckinOut,
    responses=_errors,
    summary="Create or replace the check-in for a day. The newest one updates profile weight.",
)
async def save_checkin(
    day: date, data: CheckinIn, user: CurrentUser, session: SessionDep
) -> CheckinOut:
    return await checkin_service.save(session, user, day, data)


@router.delete(
    "/{day}", status_code=status.HTTP_204_NO_CONTENT, responses={404: {"model": ErrorOut}}
)
async def delete_checkin(day: date, user: CurrentUser, session: SessionDep) -> None:
    await checkin_service.delete(session, user, day)
