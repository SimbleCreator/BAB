from collections.abc import Iterable
from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import DailyActivity


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
    rows = await session.scalars(
        select(DailyActivity.day).where(
            DailyActivity.user_id == user_id, DailyActivity.steps >= step_goal
        )
    )
    return list(rows)


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
