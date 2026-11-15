"""Habit reduction plans: setup, one-tap logging, editing past days, and status."""

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ConflictError, NotFoundError
from app.core.timeutil import local_today
from app.engines import habit_engine as eng
from app.models.habit import Habit, HabitLog
from app.models.profile import Profile
from app.models.user import User
from app.repositories import activity_repo, habit_repo, nutrition_repo, training_repo
from app.schemas.habit import (
    AvailabilityOut,
    DayLogOut,
    DayUnitsIn,
    GoalsOut,
    HabitIn,
    HabitOut,
    HabitStatusOut,
    LogIn,
    WeekResultOut,
)
from app.services import habit_progress, milestone_service, training_service
from app.services.common import require_profile

MEALS_FOR_GOAL = 2


def habit_out(h: Habit) -> HabitOut:
    return HabitOut(
        id=h.id,
        type=h.type,  # type: ignore[arg-type]
        period=h.period,  # type: ignore[arg-type]
        baseline=h.baseline,
        pace_pct=h.pace_pct,
        started_on=h.started_on,
        active=h.active,
    )


def _week_out(h: Habit, w: eng.WeekResult) -> WeekResultOut:
    start, end = eng.week_bounds(h.started_on, w.index)
    return WeekResultOut(
        number=w.index + 1,
        start=start,
        end=end,
        step=w.step,
        allowance_total=w.allowance_total,
        used=w.used,
        within=w.within,
        avoided=w.avoided,
    )


async def day_goals(
    session: AsyncSession, user: User, profile: Profile, days: list[date]
) -> dict[date, eng.DayGoals]:
    """Steps goal met, planned workout done (or rest day), and two meals logged, per day."""
    if not days:
        return {}
    start, end = min(days), max(days)
    activity = {r.day: r for r in await activity_repo.list_range(session, user.id, start, end)}
    workouts = await training_repo.sessions_between(session, user.id, start, end)
    meal_types = await nutrition_repo.meal_types_by_day(session, user.id, start, end)
    planned: set[date] = set()
    for ws in {training_service.week_start_for(d) for d in days}:
        plan = await training_repo.latest_plan(session, user.id, ws)
        if plan is not None:
            planned |= set(training_service.sessions_by_day(plan))
    out = {}
    for d in days:
        a = activity.get(d)
        steps_ok = bool(a and a.steps is not None and a.steps >= profile.daily_step_goal)
        w = workouts.get(d)
        workout_ok = (w is not None and w.status == "done") if d in planned else True
        out[d] = eng.DayGoals(steps_ok, workout_ok, meal_types.get(d, 0) >= MEALS_FOR_GOAL)
    return out


async def status(session: AsyncSession, user: User, profile: Profile, h: Habit) -> HabitStatusOut:
    today = local_today(profile.timezone)
    ref = max(today, h.started_on)
    completed = await habit_progress.completed_weeks(session, h, ref)
    step = completed[-1].step + (1 if completed[-1].within else 0) if completed else eng.FIRST_STEP
    per = eng.allowance(h.baseline, h.pace_pct, step)
    week_allow = eng.week_total_allowance(per, h.period)  # type: ignore[arg-type]
    idx = eng.week_index(h.started_on, ref)
    week_start, week_end = eng.week_bounds(h.started_on, idx)
    totals = await habit_repo.daily_totals(session, h.id, week_start, week_end)
    week_used = sum(totals.values())
    today_used = totals.get(today, 0)
    days_so_far = [
        week_start + timedelta(days=i) for i in range((min(today, week_end) - week_start).days + 1)
    ]
    goals = await day_goals(session, user, profile, days_so_far or [today])
    goals_today = goals.get(today, eng.DayGoals(False, False, False))
    if h.period == "day":
        avail = eng.daily_availability(per, goals_today, today_used)
    else:
        avail = eng.weekly_availability(per, [goals[d] for d in days_so_far], week_used)
    return HabitStatusOut(
        habit=habit_out(h),
        today=today,
        week_number=idx + 1,
        week_start=week_start,
        week_end=week_end,
        allowance_per_period=per,
        week_allowance=week_allow,
        week_used=week_used,
        today_used=today_used,
        availability=AvailabilityOut(
            period=h.period,  # type: ignore[arg-type]
            allowance=avail.allowance,
            unlocked=avail.unlocked,
            available_now=avail.available_now,
            locked=avail.locked,
            used=avail.used,
            over=avail.over,
        ),
        goals_today=GoalsOut(
            steps=goals_today.steps,
            workout=goals_today.workout,
            meals=goals_today.meals,
            met=goals_today.met,
        ),
        last_week=_week_out(h, completed[-1]) if completed else None,
        doctor_line=eng.DOCTOR_LINE,
    )


async def _get(session: AsyncSession, user: User, habit_id: int) -> Habit:
    h = await habit_repo.get(session, user.id, habit_id)
    if h is None:
        raise NotFoundError("Plan not found.", code="habit_missing")
    return h


def _check_day(h: Habit, day: date, today: date) -> None:
    if not h.active:
        raise ConflictError("This plan has ended.", code="habit_ended")
    if day > today:
        raise AppError("You cannot log a future day.", code="future_day")
    if day < h.started_on:
        raise AppError("That day is before this plan started.", code="before_start")


async def list_status(session: AsyncSession, user: User) -> list[HabitStatusOut]:
    profile = await require_profile(session, user)
    return [
        await status(session, user, profile, h) for h in await habit_repo.active(session, user.id)
    ]


async def create(session: AsyncSession, user: User, data: HabitIn) -> HabitStatusOut:
    profile = await require_profile(session, user)
    if await habit_repo.active_of_type(session, user.id, data.type):
        raise ConflictError(f"You already have a {data.type} plan.", code="habit_exists")
    h = Habit(
        user_id=user.id,
        type=data.type,
        baseline=data.baseline,
        period=eng.PERIOD_FOR[data.type],
        pace_pct=data.pace_pct,
        started_on=local_today(profile.timezone),
        active=True,
    )
    habit_repo.add(session, h)
    await session.commit()
    await session.refresh(h)
    return await status(session, user, profile, h)


async def log_one(session: AsyncSession, user: User, habit_id: int, data: LogIn) -> HabitStatusOut:
    profile = await require_profile(session, user)
    h = await _get(session, user, habit_id)
    today = local_today(profile.timezone)
    day = data.day or today
    _check_day(h, day, today)
    habit_repo.add(session, HabitLog(habit_id=h.id, day=day, units=1))
    await session.flush()
    await milestone_service.evaluate(session, user.id)
    await session.commit()
    return await status(session, user, profile, h)


async def set_day(
    session: AsyncSession, user: User, habit_id: int, day: date, data: DayUnitsIn
) -> HabitStatusOut:
    profile = await require_profile(session, user)
    h = await _get(session, user, habit_id)
    _check_day(h, day, local_today(profile.timezone))
    await habit_repo.clear_day(session, h.id, day)
    if data.units:
        habit_repo.add(session, HabitLog(habit_id=h.id, day=day, units=data.units))
    await session.flush()
    await milestone_service.evaluate(session, user.id)
    await session.commit()
    return await status(session, user, profile, h)


async def days(
    session: AsyncSession, user: User, habit_id: int, start: date, end: date
) -> list[DayLogOut]:
    h = await _get(session, user, habit_id)
    if end < start or (end - start).days > 92:
        raise AppError("Ask for up to 93 days at once.", code="bad_range")
    totals = await habit_repo.daily_totals(session, h.id, start, end)
    return [DayLogOut(day=d, units=n) for d, n in sorted(totals.items())]


async def weeks(session: AsyncSession, user: User, habit_id: int) -> list[WeekResultOut]:
    profile = await require_profile(session, user)
    h = await _get(session, user, habit_id)
    done = await habit_progress.completed_weeks(session, h, local_today(profile.timezone))
    return [_week_out(h, w) for w in reversed(done)]


async def stop(session: AsyncSession, user: User, habit_id: int) -> HabitOut:
    h = await _get(session, user, habit_id)
    h.active = False
    await session.commit()
    return habit_out(h)


async def delete(session: AsyncSession, user: User, habit_id: int) -> None:
    h = await _get(session, user, habit_id)
    await habit_repo.remove(session, h)
    await session.commit()
