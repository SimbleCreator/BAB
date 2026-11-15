"""Milestone evaluation. Called after every change to activity, runs, workouts,
meals, check-ins or habit logs, inside the caller's transaction."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import utcnow
from app.core.timeutil import local_today
from app.engines import activity_engine
from app.engines import milestone_engine as eng
from app.models.user import User
from app.repositories import (
    activity_repo,
    checkin_repo,
    milestone_repo,
    nutrition_repo,
    profile_repo,
    run_repo,
    training_repo,
)
from app.schemas.milestone import MilestoneBrief, MilestoneOut
from app.services import habit_progress


async def gather_stats(session: AsyncSession, user_id: int) -> eng.ProgressStats:
    best_day, total_steps = await activity_repo.step_totals(session, user_id)
    run_count, longest_run, total_run = await run_repo.totals(session, user_id)
    profile = await profile_repo.get(session, user_id)
    streak = 0
    if profile is not None:
        days = await activity_repo.goal_days(session, user_id, profile.daily_step_goal)
        streak = activity_engine.longest_streak(days)
    return eng.ProgressStats(
        best_day_steps=best_day,
        total_steps=total_steps,
        run_count=run_count,
        longest_run_m=longest_run,
        total_run_m=total_run,
        longest_step_streak=streak,
        checkin_count=await checkin_repo.count(session, user_id),
        workout_count=await training_repo.count_done(session, user_id),
        meal_days=await nutrition_repo.meal_days(session, user_id),
        habit_weeks_within=(
            await habit_progress.weeks_within(session, user_id, local_today(profile.timezone))
            if profile is not None
            else 0
        ),
    )


async def evaluate(session: AsyncSession, user_id: int) -> list[str]:
    """Unlock anything newly earned. Does not commit; the caller's transaction does."""
    stats = await gather_stats(session, user_id)
    already = await milestone_repo.unlocked(session, user_id)
    new = eng.newly_unlocked(stats, already.keys())
    await milestone_repo.unlock(session, user_id, new, utcnow())
    return new


async def evaluate_and_commit(session: AsyncSession, user_id: int) -> None:
    """Catch up on anything earned by data saved before a milestone existed."""
    if await evaluate(session, user_id):
        await session.commit()


async def list_milestones(session: AsyncSession, user: User) -> list[MilestoneOut]:
    await evaluate_and_commit(session, user.id)
    stats = await gather_stats(session, user.id)
    unlocked = await milestone_repo.unlocked(session, user.id)
    out = []
    for m in eng.MILESTONES:
        row = unlocked.get(m.code)
        current = eng.current_value(m, stats)
        out.append(
            MilestoneOut(
                code=m.code,
                title=m.title,
                description=m.description,
                category=m.category,
                target=m.target,
                current=m.target if row else min(current, m.target),
                unit=m.unit,
                unlocked_at=row.unlocked_at if row else None,
                seen=bool(row and row.seen_at),
            )
        )
    return out


async def unseen(session: AsyncSession, user_id: int) -> list[MilestoneBrief]:
    rows = await milestone_repo.unseen(session, user_id)
    return [
        MilestoneBrief(code=r.code, title=eng.BY_CODE[r.code].title)
        for r in rows
        if r.code in eng.BY_CODE
    ]


async def mark_seen(session: AsyncSession, user: User) -> None:
    await milestone_repo.mark_seen(session, user.id, utcnow())
    await session.commit()
