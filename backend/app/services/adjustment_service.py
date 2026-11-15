"""Weekly adjustment: runs after a check-in and changes calories and training."""

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.content import exercise_library
from app.core.timeutil import local_today
from app.engines import adjustment_engine as eng
from app.engines import nutrition_engine
from app.models.adjustment import WeeklyAdjustment
from app.models.profile import Profile
from app.models.user import User
from app.repositories import adjustment_repo, checkin_repo, nutrition_repo
from app.schemas.adjustment import AdjustmentOut, NutritionChangeOut, TrainingChangeOut
from app.services import nutrition_service, training_service

MIN_DAYS_BETWEEN = 6  # weekly, with a day of slack


def to_out(row: WeeklyAdjustment) -> AdjustmentOut:
    s = row.summary
    return AdjustmentOut(
        id=row.id,
        checkin_day=row.checkin_day,
        reference_day=date.fromisoformat(s["reference_day"]),
        created_at=row.created_at,
        weekly_change_pct=s["weekly_change_pct"],
        nutrition=NutritionChangeOut(**s["nutrition"]),
        training=TrainingChangeOut(**s["training"]),
        summary=s["lines"],
    )


async def maybe_adjust(
    session: AsyncSession, user: User, profile: Profile, checkin_day: date
) -> tuple[AdjustmentOut | None, str | None]:
    """Run the adjustment for a just-saved check-in if the rules allow it.

    Returns (adjustment, None) when it ran, or (None, note) explaining why not.
    Does not commit.
    """
    checkins = await checkin_repo.list_all(session, user.id)
    if len(checkins) < 2:
        return None, "Your first check-in sets the starting point. Adjustments start next week."
    latest = checkins[-1]
    if latest.day != checkin_day:
        return None, "Only your newest check-in adjusts the plan."
    if await adjustment_repo.for_day(session, user.id, checkin_day) is not None:
        return None, "This check-in already adjusted your plan. Changes to it do not run it again."
    last = await adjustment_repo.latest(session, user.id)
    if last is not None and (checkin_day - last.checkin_day).days < MIN_DAYS_BETWEEN:
        nxt = last.checkin_day + timedelta(days=MIN_DAYS_BETWEEN)
        return None, f"Plans adjust once a week. The next check-in from {nxt:%d %b} will adjust it."
    reference = next(
        (c for c in reversed(checkins[:-1]) if (checkin_day - c.day).days >= MIN_DAYS_BETWEEN),
        None,
    )
    if reference is None:
        return None, "Check in again about a week after your previous check-in to adjust the plan."

    # Nutrition
    pct = eng.weekly_change_pct(
        float(reference.weight_kg), float(latest.weight_kg), (latest.day - reference.day).days
    )
    current = await nutrition_repo.target_for_day(session, user.id, checkin_day)
    before = (
        current.calories_kcal
        if current
        else (nutrition_service.breakdown(profile).targets.calories_kcal)
    )
    floor = nutrition_engine.floor_for(profile.sex)  # type: ignore[arg-type]
    n = eng.nutrition_decision(profile.goal, pct, before, floor)
    if n.new_kcal != before or current is None:
        await nutrition_service.set_target_calories(
            session, user, profile, n.new_kcal, f"Weekly check-in: {n.reason}"
        )

    # Training
    week = await training_service.last_week(session, user, checkin_day)
    plan = await training_service.ensure_plan(
        session, user, profile, training_service.week_start_for(local_today(profile.timezone))
    )
    result = eng.apply_training(
        training_service.template_of(plan),
        week,
        exercise_library().by_code(),
        training_service.training_input(profile),
    )
    t_summary = eng.training_summary(week, result)
    if result.changes:
        await training_service.apply_adjusted_template(
            session,
            user,
            profile,
            list(result.sessions),
            note=f"Updated after your check-in on {checkin_day:%d %b}. {t_summary}",
        )

    change = n.new_kcal - before
    lines = [n.reason]
    if change:
        lines.append(f"Daily target: {before} to {n.new_kcal} kcal.")
    lines.append(t_summary)
    if result.decision == "progress":
        lines += result.changes  # the reduce summary already says it
    summary = {
        "reference_day": reference.day.isoformat(),
        "weekly_change_pct": n.weekly_change_pct,
        "nutrition": {
            "before_kcal": before,
            "after_kcal": n.new_kcal,
            "change_kcal": change,
            "floor_applied": n.floor_applied,
            "reason": n.reason,
        },
        "training": {
            "decision": result.decision,
            "planned_sessions": week.planned_sessions,
            "done_sessions": week.done_sessions,
            "completion_pct": round(week.completion * 100),
            "changes": list(result.changes),
            "summary": t_summary,
        },
        "lines": lines,
    }
    row = WeeklyAdjustment(user_id=user.id, checkin_day=checkin_day, summary=summary)
    adjustment_repo.add(session, row)
    await session.flush()
    await session.refresh(row)
    return to_out(row), None


async def list_adjustments(session: AsyncSession, user: User) -> list[AdjustmentOut]:
    return [to_out(r) for r in await adjustment_repo.list_all(session, user.id)]
