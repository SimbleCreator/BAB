from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, SessionDep
from app.schemas.common import ErrorOut
from app.schemas.habit import (
    DayLogOut,
    DayUnitsIn,
    HabitIn,
    HabitOut,
    HabitStatusOut,
    LogIn,
    WeekResultOut,
)
from app.services import habit_service as svc

router = APIRouter(prefix="/habits", tags=["habits"])

_errors = {400: {"model": ErrorOut}, 404: {"model": ErrorOut}, 409: {"model": ErrorOut}}


@router.get("", response_model=list[HabitStatusOut], summary="Active reduction plans with status")
async def list_habits(user: CurrentUser, session: SessionDep) -> list[HabitStatusOut]:
    return await svc.list_status(session, user)


@router.post(
    "",
    response_model=HabitStatusOut,
    status_code=status.HTTP_201_CREATED,
    responses=_errors,
    summary="Start a reduction plan (one active plan per type)",
)
async def create_habit(data: HabitIn, user: CurrentUser, session: SessionDep) -> HabitStatusOut:
    return await svc.create(session, user, data)


@router.post(
    "/{habit_id}/log",
    response_model=HabitStatusOut,
    responses=_errors,
    summary="One-tap: record one cigarette or drink (today unless `day` is given)",
)
async def log_one(
    habit_id: int, user: CurrentUser, session: SessionDep, data: LogIn | None = None
) -> HabitStatusOut:
    return await svc.log_one(session, user, habit_id, data or LogIn())


@router.put(
    "/{habit_id}/days/{day}",
    response_model=HabitStatusOut,
    responses=_errors,
    summary="Set the total for a day (to correct or fill in past days)",
)
async def set_day(
    habit_id: int, day: date, data: DayUnitsIn, user: CurrentUser, session: SessionDep
) -> HabitStatusOut:
    return await svc.set_day(session, user, habit_id, day, data)


@router.get("/{habit_id}/days", response_model=list[DayLogOut], responses=_errors)
async def list_days(
    habit_id: int,
    user: CurrentUser,
    session: SessionDep,
    start: Annotated[date, Query(alias="from")],
    end: Annotated[date, Query(alias="to")],
) -> list[DayLogOut]:
    return await svc.days(session, user, habit_id, start, end)


@router.get(
    "/{habit_id}/weeks",
    response_model=list[WeekResultOut],
    responses=_errors,
    summary="Finished weeks of the plan, newest first",
)
async def list_weeks(habit_id: int, user: CurrentUser, session: SessionDep) -> list[WeekResultOut]:
    return await svc.weeks(session, user, habit_id)


@router.post("/{habit_id}/stop", response_model=HabitOut, responses=_errors)
async def stop_habit(habit_id: int, user: CurrentUser, session: SessionDep) -> HabitOut:
    return await svc.stop(session, user, habit_id)


@router.delete(
    "/{habit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_errors,
    summary="Delete a plan and all of its logs",
)
async def delete_habit(habit_id: int, user: CurrentUser, session: SessionDep) -> None:
    await svc.delete(session, user, habit_id)
