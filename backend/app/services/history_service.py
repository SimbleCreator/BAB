"""History: a month overview and everything recorded on one day."""

import calendar
import re
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.timeutil import local_today
from app.models.user import User
from app.repositories import (
    activity_repo,
    checkin_repo,
    habit_repo,
    nutrition_repo,
    run_repo,
    training_repo,
)
from app.schemas.history import HabitDayOut, HistoryDayOut, MonthDayOut, MonthOut
from app.services import (
    activity_service,
    checkin_service,
    nutrition_service,
    run_service,
    training_service,
)
from app.services.common import require_profile

MONTH_RE = re.compile(r"^(\d{4})-(\d{2})$")


def _parse_month(month: str) -> tuple[date, date]:
    m = MONTH_RE.match(month)
    if not m or not 1 <= int(m.group(2)) <= 12:
        raise AppError("Month must look like 2026-01.", code="bad_month")
    year, mon = int(m.group(1)), int(m.group(2))
    return date(year, mon, 1), date(year, mon, calendar.monthrange(year, mon)[1])


async def month(session: AsyncSession, user: User, month_str: str | None) -> MonthOut:
    profile = await require_profile(session, user)
    today = local_today(profile.timezone)
    start, end = _parse_month(month_str or f"{today:%Y-%m}")
    if start > today:
        raise AppError("That month has not started yet.", code="future_month")
    activity = {r.day for r in await activity_repo.list_range(session, user.id, start, end)}
    workouts = await training_repo.sessions_between(session, user.id, start, end)
    meals = await nutrition_repo.daily_calories(session, user.id, start, end)
    checkins = {
        c.day for c in await checkin_repo.list_all(session, user.id) if start <= c.day <= end
    }
    runs = await run_repo.counts_by_day(session, user.id, start, end)
    days = []
    for i in range((end - start).days + 1):
        d = start + timedelta(days=i)
        w = workouts.get(d)
        days.append(
            MonthDayOut(
                day=d,
                activity=d in activity,
                workout=w.status if w else None,  # type: ignore[arg-type]
                meals=d in meals,
                checkin=d in checkins,
                runs=runs.get(d, 0),
            )
        )
    return MonthOut(month=f"{start:%Y-%m}", today=today, days=days)


async def day(session: AsyncSession, user: User, d: date) -> HistoryDayOut:
    profile = await require_profile(session, user)
    today = local_today(profile.timezone)
    if d > today:
        raise AppError("That day has not happened yet.", code="future_day")
    row = await activity_repo.get(session, user.id, d)
    activity = activity_service.to_out(row, profile) if row else None
    runs = await run_service.runs_on(session, user, d)

    plan = await training_repo.latest_plan(session, user.id, training_service.week_start_for(d))
    planned = training_service.sessions_by_day(plan).get(d) if plan else None
    logged = await training_repo.get_session(session, user.id, d)

    checkins = await checkin_service.list_checkins(session, user)
    checkin = next((c for c in checkins if c.day == d), None)

    habits = []
    for h in await habit_repo.all_for_user(session, user.id):
        units = (await habit_repo.daily_totals(session, h.id, d, d)).get(d, 0)
        if units or (h.active and h.started_on <= d):
            habits.append(HabitDayOut(habit_id=h.id, type=h.type, units=units))

    return HistoryDayOut(
        day=d,
        today=today,
        activity=activity,
        runs=runs,
        workout_title=planned.title if planned else None,
        workout=training_service.workout_out(logged) if logged else None,
        nutrition=await nutrition_service.get_day(session, user, d),
        checkin=checkin,
        habits=habits,
    )
