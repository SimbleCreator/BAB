from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.milestone import Milestone


async def unlocked(session: AsyncSession, user_id: int) -> dict[str, Milestone]:
    rows = await session.scalars(select(Milestone).where(Milestone.user_id == user_id))
    return {m.code: m for m in rows}


async def unlock(session: AsyncSession, user_id: int, codes: list[str], now: datetime) -> None:
    if not codes:
        return
    # ON CONFLICT DO NOTHING: a concurrent request may unlock the same milestone.
    await session.execute(
        insert(Milestone)
        .values([{"user_id": user_id, "code": c, "unlocked_at": now} for c in codes])
        .on_conflict_do_nothing(index_elements=["user_id", "code"])
    )


async def unseen(session: AsyncSession, user_id: int) -> list[Milestone]:
    rows = await session.scalars(
        select(Milestone)
        .where(Milestone.user_id == user_id, Milestone.seen_at.is_(None))
        .order_by(Milestone.unlocked_at)
    )
    return list(rows)


async def mark_seen(session: AsyncSession, user_id: int, now: datetime) -> None:
    await session.execute(
        update(Milestone)
        .where(Milestone.user_id == user_id, Milestone.seen_at.is_(None))
        .values(seen_at=now)
    )
