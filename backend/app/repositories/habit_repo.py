from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.habit import Habit, HabitLog


async def active(session: AsyncSession, user_id: int) -> list[Habit]:
    rows = await session.scalars(
        select(Habit).where(Habit.user_id == user_id, Habit.active).order_by(Habit.id)
    )
    return list(rows)


async def all_for_user(session: AsyncSession, user_id: int) -> list[Habit]:
    rows = await session.scalars(select(Habit).where(Habit.user_id == user_id).order_by(Habit.id))
    return list(rows)


async def get(session: AsyncSession, user_id: int, habit_id: int) -> Habit | None:
    return await session.scalar(select(Habit).where(Habit.id == habit_id, Habit.user_id == user_id))


async def active_of_type(session: AsyncSession, user_id: int, kind: str) -> Habit | None:
    return await session.scalar(
        select(Habit).where(Habit.user_id == user_id, Habit.type == kind, Habit.active)
    )


def add(session: AsyncSession, row) -> None:
    session.add(row)


async def daily_totals(
    session: AsyncSession, habit_id: int, start: date, end: date
) -> dict[date, int]:
    rows = await session.execute(
        select(HabitLog.day, func.sum(HabitLog.units))
        .where(HabitLog.habit_id == habit_id, HabitLog.day >= start, HabitLog.day <= end)
        .group_by(HabitLog.day)
    )
    return {d: int(n or 0) for d, n in rows.all()}


async def clear_day(session: AsyncSession, habit_id: int, day: date) -> None:
    await session.execute(
        delete(HabitLog).where(HabitLog.habit_id == habit_id, HabitLog.day == day)
    )


async def remove(session: AsyncSession, habit: Habit) -> None:
    await session.delete(habit)
