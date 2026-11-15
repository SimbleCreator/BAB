from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, SessionDep
from app.schemas.common import ErrorOut
from app.schemas.training import ExerciseOut, WeekOut, WorkoutIn, WorkoutOut
from app.services import training_service

router = APIRouter(tags=["training"])

_errors = {400: {"model": ErrorOut}, 409: {"model": ErrorOut}}


@router.get("/exercises", response_model=list[ExerciseOut], summary="The exercise library")
async def list_exercises(_: CurrentUser) -> list[ExerciseOut]:
    return training_service.list_exercises()


@router.get("/exercises/{code}", response_model=ExerciseOut, responses={404: {"model": ErrorOut}})
async def get_exercise(code: str, _: CurrentUser) -> ExerciseOut:
    return training_service.get_exercise(code)


@router.get(
    "/training/week",
    response_model=WeekOut,
    responses=_errors,
    summary="The plan for the week containing `day` (default today), with what was logged",
)
async def get_week(
    user: CurrentUser, session: SessionDep, day: Annotated[date | None, Query()] = None
) -> WeekOut:
    return await training_service.get_week(session, user, day)


@router.get(
    "/training/workouts/{day}", response_model=WorkoutOut, responses={404: {"model": ErrorOut}}
)
async def get_workout(day: date, user: CurrentUser, session: SessionDep) -> WorkoutOut:
    return await training_service.get_workout(session, user, day)


@router.put(
    "/training/workouts/{day}",
    response_model=WorkoutOut,
    responses=_errors,
    summary="Save (or replace) the workout for a planned day, done or skipped",
)
async def save_workout(
    day: date, data: WorkoutIn, user: CurrentUser, session: SessionDep
) -> WorkoutOut:
    return await training_service.save_workout(session, user, day, data)


@router.delete(
    "/training/workouts/{day}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorOut}},
)
async def delete_workout(day: date, user: CurrentUser, session: SessionDep) -> None:
    await training_service.delete_workout(session, user, day)
