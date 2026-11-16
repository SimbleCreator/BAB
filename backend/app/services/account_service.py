"""Data export, account deletion, public config and admin aggregates."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, inspect, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import utcnow, verify_password
from app.models import (
    BounceLetter,
    BouncePlan,
    Checkin,
    CustomFood,
    DailyActivity,
    EasyDay,
    GymProfile,
    Habit,
    HabitLog,
    Meal,
    MealItem,
    Milestone,
    NutritionTarget,
    Profile,
    RefreshToken,
    Run,
    RunPoint,
    TrainingPlan,
    User,
    WeeklyAdjustment,
    WorkoutSession,
    WorkoutSet,
)
from app.schemas.account import (
    AdminStatsOut,
    DeleteAccountIn,
    ExportOut,
    PublicConfigOut,
    WeekCount,
)

SKIP = {"user_id"}  # implied by the export itself


def _value(v: Any) -> Any:
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return v


def _row(obj: Any, skip: set[str] = SKIP) -> dict[str, Any]:
    return {
        c.key: _value(getattr(obj, c.key))
        for c in inspect(obj).mapper.column_attrs
        if c.key not in skip
    }


async def _all(session: AsyncSession, model, *where, order=None) -> list:
    stmt = select(model).where(*where)
    if order is not None:
        stmt = stmt.order_by(order)
    return list(await session.scalars(stmt))


async def export(session: AsyncSession, user: User) -> ExportOut:
    uid = user.id
    profile = await session.get(Profile, uid)

    runs = []
    for r in await _all(session, Run, Run.user_id == uid, order=Run.day):
        points = await _all(session, RunPoint, RunPoint.run_id == r.id, order=RunPoint.seq)
        runs.append(_row(r) | {"points": [_row(p, {"run_id"}) for p in points]})

    workouts = []
    for w in await _all(
        session, WorkoutSession, WorkoutSession.user_id == uid, order=WorkoutSession.day
    ):
        sets = await _all(session, WorkoutSet, WorkoutSet.session_id == w.id, order=WorkoutSet.id)
        workouts.append(_row(w) | {"sets": [_row(s, {"session_id"}) for s in sets]})

    meals = []
    for m in await _all(session, Meal, Meal.user_id == uid, order=Meal.day):
        items = await _all(session, MealItem, MealItem.meal_id == m.id, order=MealItem.id)
        meals.append(_row(m) | {"items": [_row(i, {"meal_id"}) for i in items]})

    habits = []
    for h in await _all(session, Habit, Habit.user_id == uid, order=Habit.id):
        logs = await _all(session, HabitLog, HabitLog.habit_id == h.id, order=HabitLog.day)
        habits.append(_row(h) | {"logs": [_row(x, {"habit_id"}) for x in logs]})

    async def rows(model, *where, order=None) -> list[dict[str, Any]]:
        return [_row(x) for x in await _all(session, model, *where, order=order)]

    return ExportOut(
        exported_at=utcnow(),
        account={
            "email": user.email,
            "created_at": _value(user.created_at),
            "consent_at": _value(user.consent_at),
            "last_login_at": _value(user.last_login_at),
            "is_admin": user.is_admin,
        },
        profile=_row(profile) if profile else None,
        daily_activity=await rows(
            DailyActivity, DailyActivity.user_id == uid, order=DailyActivity.day
        ),
        runs=runs,
        training_plans=await rows(TrainingPlan, TrainingPlan.user_id == uid, order=TrainingPlan.id),
        workouts=workouts,
        nutrition_targets=await rows(
            NutritionTarget, NutritionTarget.user_id == uid, order=NutritionTarget.id
        ),
        custom_foods=await rows(CustomFood, CustomFood.user_id == uid, order=CustomFood.id),
        meals=meals,
        checkins=await rows(Checkin, Checkin.user_id == uid, order=Checkin.day),
        weekly_adjustments=await rows(
            WeeklyAdjustment, WeeklyAdjustment.user_id == uid, order=WeeklyAdjustment.checkin_day
        ),
        milestones=await rows(Milestone, Milestone.user_id == uid, order=Milestone.unlocked_at),
        habits=habits,
        gym_profile=_row(gym) if (gym := await session.get(GymProfile, uid)) else None,
        bounce_plans=await rows(BouncePlan, BouncePlan.user_id == uid, order=BouncePlan.id),
        bounce_letters=await rows(BounceLetter, BounceLetter.user_id == uid, order=BounceLetter.id),
        easy_days=await rows(EasyDay, EasyDay.user_id == uid, order=EasyDay.day),
    )


async def delete_account(session: AsyncSession, user: User, data: DeleteAccountIn) -> None:
    """Permanent: the database cascades the delete to every row the user owns."""
    if user.password_hash is not None:
        if not verify_password(user.password_hash, data.password or ""):
            raise AppError("Password is wrong.", code="wrong_password")
    elif (data.email or "").strip().lower() != user.email:
        raise AppError("Type your account email to confirm.", code="wrong_email")
    await session.delete(user)
    await session.commit()


def public_config() -> PublicConfigOut:
    s = get_settings()
    return PublicConfigOut(app_name=s.app_name, contact_email=s.contact_email, version=s.version)


RECORD_TYPES = {
    "daily_activity": DailyActivity,
    "runs": Run,
    "workouts": WorkoutSession,
    "meals": Meal,
    "meal_items": MealItem,
    "custom_foods": CustomFood,
    "checkins": Checkin,
    "milestones": Milestone,
    "habits": Habit,
    "habit_logs": HabitLog,
    "bounce_plans": BouncePlan,
    "bounce_letters": BounceLetter,
    "easy_days": EasyDay,
}


async def admin_stats(session: AsyncSession) -> AdminStatsOut:
    now = utcnow()

    async def active_since(days: int) -> int:
        cutoff = now - timedelta(days=days)
        recent_refresh = select(RefreshToken.user_id).where(RefreshToken.created_at >= cutoff)
        return (
            await session.scalar(
                select(func.count()).where(
                    or_(User.last_login_at >= cutoff, User.id.in_(recent_refresh))
                )
            )
            or 0
        )

    this_monday = now.date() - timedelta(days=now.date().weekday())
    first = this_monday - timedelta(weeks=11)
    created = await session.execute(
        select(User.created_at).where(
            User.created_at >= datetime.combine(first, datetime.min.time(), now.tzinfo)
        )
    )
    per_week = {first + timedelta(weeks=i): 0 for i in range(12)}
    for (ts,) in created.all():
        d = ts.date()
        per_week[d - timedelta(days=d.weekday())] = (
            per_week.get(d - timedelta(days=d.weekday()), 0) + 1
        )

    records = {}
    for name, model in RECORD_TYPES.items():
        records[name] = await session.scalar(select(func.count()).select_from(model)) or 0

    return AdminStatsOut(
        total_users=await session.scalar(select(func.count()).select_from(User)) or 0,
        active_7_days=await active_since(7),
        active_30_days=await active_since(30),
        new_users_per_week=[WeekCount(week_start=k, count=v) for k, v in sorted(per_week.items())],
        records=records,
    )
