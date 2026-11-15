from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bounce import BouncePlan, GymProfile


async def gym_profile(session: AsyncSession, user_id: int) -> GymProfile | None:
    return await session.get(GymProfile, user_id)


async def latest_plan(session: AsyncSession, user_id: int) -> BouncePlan | None:
    return await session.scalar(
        select(BouncePlan)
        .where(BouncePlan.user_id == user_id)
        .order_by(BouncePlan.created_at.desc(), BouncePlan.id.desc())
        .limit(1)
    )


async def plans_since(session: AsyncSession, user_id: int, since: datetime) -> int:
    return (
        await session.scalar(
            select(func.count()).where(
                BouncePlan.user_id == user_id, BouncePlan.created_at >= since
            )
        )
        or 0
    )


def add(session: AsyncSession, row: object) -> None:
    session.add(row)
