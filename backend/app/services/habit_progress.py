"""Shared habit calculations, used by the habit service, Today and milestones."""

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.engines import habit_engine as eng
from app.models.habit import Habit
from app.repositories import habit_repo


async def completed_weeks(session: AsyncSession, habit: Habit, today: date) -> list[eng.WeekResult]:
    """Results for every week of the plan that has ended before today."""
    current = eng.week_index(habit.started_on, today)
    if current <= 0:
        return []
    end = habit.started_on + timedelta(days=7 * current - 1)
    totals = await habit_repo.daily_totals(session, habit.id, habit.started_on, end)
    week_totals = [0] * current
    for d, n in totals.items():
        week_totals[eng.week_index(habit.started_on, d)] += n
    results, _ = eng.weeks(habit.baseline, habit.pace_pct, habit.period, week_totals)  # type: ignore[arg-type]
    return results


async def weeks_within(session: AsyncSession, user_id: int, today: date) -> int:
    """Completed weeks inside the allowance, across all of the user's plans."""
    count = 0
    for habit in await habit_repo.all_for_user(session, user_id):
        count += sum(1 for w in await completed_weeks(session, habit, today) if w.within)
    return count
