from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.run import Run, RunPoint

_has_track = exists().where(RunPoint.run_id == Run.id).correlate(Run).label("has_track")


async def list_for_user(
    session: AsyncSession, user_id: int, limit: int, offset: int
) -> tuple[list[tuple[Run, bool]], int]:
    rows = await session.execute(
        select(Run, _has_track)
        .where(Run.user_id == user_id)
        .order_by(Run.day.desc(), Run.started_at.desc().nulls_last(), Run.id.desc())
        .limit(limit)
        .offset(offset)
    )
    total = await session.scalar(select(func.count()).where(Run.user_id == user_id))
    return [(r, bool(t)) for r, t in rows.all()], total or 0


async def get(session: AsyncSession, user_id: int, run_id: int, *, with_points: bool = False):
    stmt = select(Run).where(Run.id == run_id, Run.user_id == user_id)
    if with_points:
        stmt = stmt.options(selectinload(Run.points)).execution_options(populate_existing=True)
    return await session.scalar(stmt)


async def has_track(session: AsyncSession, run_id: int) -> bool:
    return bool(await session.scalar(select(exists().where(RunPoint.run_id == run_id))))


def add(session: AsyncSession, run: Run) -> None:
    session.add(run)


async def delete(session: AsyncSession, run: Run) -> None:
    await session.delete(run)


async def totals(session: AsyncSession, user_id: int) -> tuple[int, int, int]:
    """(count, longest distance, total distance) in metres."""
    row = (
        await session.execute(
            select(
                func.count(Run.id),
                func.coalesce(func.max(Run.distance_m), 0),
                func.coalesce(func.sum(Run.distance_m), 0),
            ).where(Run.user_id == user_id)
        )
    ).one()
    return int(row[0]), int(row[1]), int(row[2])
