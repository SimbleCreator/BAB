from collections.abc import Iterable
from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import DailyActivity, EasyDay
from app.models.nutrition import Meal
from app.models.training import WorkoutSession


async def get(session: AsyncSession, user_id: int, day: date) -> DailyActivity | None:
    return await session.scalar(
        select(DailyActivity).where(DailyActivity.user_id == user_id, DailyActivity.day == day)
    )


async def list_range(
    session: AsyncSession, user_id: int, start: date, end: date
) -> list[DailyActivity]:
    rows = await session.scalars(
        select(DailyActivity)
        .where(
            DailyActivity.user_id == user_id,
            DailyActivity.day >= start,
            DailyActivity.day <= end,
        )
        .order_by(DailyActivity.day)
    )
    return list(rows)


async def goal_days(session: AsyncSession, user_id: int, step_goal: int) -> list[date]:
    """Days that count for step-goal streaks: the goal was met, or it was an easy day."""
    met = await session.scalars(
        select(DailyActivity.day).where(
            DailyActivity.user_id == user_id, DailyActivity.steps >= step_goal
        )
    )
    return sorted(set(met) | set(await easy_days(session, user_id)))


async def easy_days(session: AsyncSession, user_id: int) -> list[date]:
    rows = await session.scalars(
        select(EasyDay.day).where(EasyDay.user_id == user_id).order_by(EasyDay.day)
    )
    return list(rows)


async def get_easy_day(session: AsyncSession, user_id: int, day: date) -> EasyDay | None:
    return await session.scalar(
        select(EasyDay).where(EasyDay.user_id == user_id, EasyDay.day == day)
    )


async def logged_days(session: AsyncSession, user_id: int, start: date, end: date) -> set[date]:
    """Days with any activity numbers, workout or meal between start and end."""
    out: set[date] = set()
    for model in (DailyActivity, WorkoutSession, Meal):
        rows = await session.scalars(
            select(model.day).where(model.user_id == user_id, model.day >= start, model.day <= end)
        )
        out |= set(rows)
    return out


async def by_days(
    session: AsyncSession, user_id: int, days: Iterable[date]
) -> dict[date, DailyActivity]:
    days = list(days)
    if not days:
        return {}
    rows = await session.scalars(
        select(DailyActivity).where(DailyActivity.user_id == user_id, DailyActivity.day.in_(days))
    )
    return {r.day: r for r in rows}


def add(session: AsyncSession, row: DailyActivity) -> None:
    session.add(row)


async def remove(session: AsyncSession, user_id: int, day: date) -> bool:
    result = await session.execute(
        delete(DailyActivity).where(DailyActivity.user_id == user_id, DailyActivity.day == day)
    )
    return result.rowcount > 0


async def step_totals(session: AsyncSession, user_id: int) -> tuple[int, int]:
    """(best single day, total) steps."""
    row = (
        await session.execute(
            select(
                func.coalesce(func.max(DailyActivity.steps), 0),
                func.coalesce(func.sum(DailyActivity.steps), 0),
            ).where(DailyActivity.user_id == user_id)
        )
    ).one()
    return int(row[0]), int(row[1])
