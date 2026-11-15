from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.checkin import Checkin


async def get(session: AsyncSession, user_id: int, day: date) -> Checkin | None:
    return await session.scalar(
        select(Checkin).where(Checkin.user_id == user_id, Checkin.day == day)
    )


async def list_all(session: AsyncSession, user_id: int) -> list[Checkin]:
    rows = await session.scalars(
        select(Checkin).where(Checkin.user_id == user_id).order_by(Checkin.day)
    )
    return list(rows)


async def latest(session: AsyncSession, user_id: int) -> Checkin | None:
    return await session.scalar(
        select(Checkin).where(Checkin.user_id == user_id).order_by(Checkin.day.desc()).limit(1)
    )


async def count(session: AsyncSession, user_id: int) -> int:
    return await session.scalar(select(func.count()).where(Checkin.user_id == user_id)) or 0


def add(session: AsyncSession, row: Checkin) -> None:
    session.add(row)


async def remove(session: AsyncSession, user_id: int, day: date) -> bool:
    result = await session.execute(
        delete(Checkin).where(Checkin.user_id == user_id, Checkin.day == day)
    )
    return result.rowcount > 0
