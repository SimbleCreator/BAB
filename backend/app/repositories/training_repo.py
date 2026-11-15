from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.training import TrainingPlan, WorkoutSession


async def latest_plan(session: AsyncSession, user_id: int, week_start: date) -> TrainingPlan | None:
    return await session.scalar(
        select(TrainingPlan)
        .where(TrainingPlan.user_id == user_id, TrainingPlan.week_start == week_start)
        .order_by(TrainingPlan.created_at.desc(), TrainingPlan.id.desc())
        .limit(1)
    )


def add(session: AsyncSession, row) -> None:
    session.add(row)


async def sessions_between(
    session: AsyncSession, user_id: int, start: date, end: date
) -> dict[date, WorkoutSession]:
    rows = await session.scalars(
        select(WorkoutSession).where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.day >= start,
            WorkoutSession.day <= end,
        )
    )
    return {r.day: r for r in rows}


async def get_session(session: AsyncSession, user_id: int, day: date) -> WorkoutSession | None:
    return await session.scalar(
        select(WorkoutSession)
        .where(WorkoutSession.user_id == user_id, WorkoutSession.day == day)
        .options(selectinload(WorkoutSession.sets))
        .execution_options(populate_existing=True)
    )


async def remove_session(session: AsyncSession, user_id: int, day: date) -> bool:
    result = await session.execute(
        delete(WorkoutSession).where(WorkoutSession.user_id == user_id, WorkoutSession.day == day)
    )
    return result.rowcount > 0


async def count_done(session: AsyncSession, user_id: int) -> int:
    return (
        await session.scalar(
            select(func.count()).where(
                WorkoutSession.user_id == user_id, WorkoutSession.status == "done"
            )
        )
        or 0
    )
