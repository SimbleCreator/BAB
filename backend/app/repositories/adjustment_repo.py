from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.adjustment import WeeklyAdjustment


async def for_day(session: AsyncSession, user_id: int, day: date) -> WeeklyAdjustment | None:
    return await session.scalar(
        select(WeeklyAdjustment).where(
            WeeklyAdjustment.user_id == user_id, WeeklyAdjustment.checkin_day == day
        )
    )


async def latest(session: AsyncSession, user_id: int) -> WeeklyAdjustment | None:
    return await session.scalar(
        select(WeeklyAdjustment)
        .where(WeeklyAdjustment.user_id == user_id)
        .order_by(WeeklyAdjustment.checkin_day.desc())
        .limit(1)
    )


async def list_all(session: AsyncSession, user_id: int) -> list[WeeklyAdjustment]:
    rows = await session.scalars(
        select(WeeklyAdjustment)
        .where(WeeklyAdjustment.user_id == user_id)
        .order_by(WeeklyAdjustment.checkin_day.desc())
    )
    return list(rows)


def add(session: AsyncSession, row: WeeklyAdjustment) -> None:
    session.add(row)
