"""Bounce: weekly AI plans for Activity, Train or both, beside the rule engines."""

import logging
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.content import foods_by_code, states_by_code
from app.core.config import get_settings
from app.core.errors import (
    ConflictError,
    NotFoundError,
    RateLimitError,
    UnavailableError,
    UpstreamError,
)
from app.core.timeutil import local_today
from app.engines import checkin_engine
from app.models.bounce import BouncePlan, GymProfile
from app.models.profile import Profile
from app.models.user import User
from app.repositories import (
    activity_repo,
    bounce_repo,
    checkin_repo,
    nutrition_repo,
    training_repo,
)
from app.schemas.bounce import (
    BounceNotificationOut,
    BouncePlanOut,
    BounceStatusOut,
    GymProfileIn,
    GymProfileOut,
    PlanContent,
    Targets,
)
from app.services.bounce import rules
from app.services.bounce.llm import LLMClient, LLMError, extract_json
from app.services.bounce.prompt import (
    BounceContext,
    CheckinPoint,
    GymInfo,
    Lifestyle,
    build_messages,
)
from app.services.common import require_profile
from app.services.nutrition_service import breakdown

log = logging.getLogger(__name__)

MAX_TOKENS = 3500
STEPS_PER_MINUTE = 100  # brisk walking, used for "a N-minute walk" hints


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _local_date(ts: datetime, tz: str) -> date:
    return ts.astimezone(ZoneInfo(tz)).date()


# Gym profile -------------------------------------------------------------------


def _gym_out(row: GymProfile) -> GymProfileOut:
    return GymProfileOut(
        experience=row.experience,  # type: ignore[arg-type]
        days_per_week=row.days_per_week,
        session_minutes=row.session_minutes,
        supplements=list(row.supplements or []),
        supplements_note=row.supplements_note,
        injuries_note=row.injuries_note,
        updated_at=row.updated_at,
    )


async def get_gym_profile(session: AsyncSession, user: User) -> GymProfileOut:
    row = await bounce_repo.gym_profile(session, user.id)
    if row is None:
        raise NotFoundError("No gym details yet.", code="gym_profile_missing")
    return _gym_out(row)


async def save_gym_profile(session: AsyncSession, user: User, data: GymProfileIn) -> GymProfileOut:
    row = await bounce_repo.gym_profile(session, user.id)
    if row is None:
        row = GymProfile(user_id=user.id)
        bounce_repo.add(session, row)
    row.experience = data.experience
    row.days_per_week = data.days_per_week
    row.session_minutes = data.session_minutes
    row.supplements = list(data.supplements)
    row.supplements_note = data.supplements_note
    row.injuries_note = data.injuries_note
    row.updated_at = _now()
    await session.commit()
    return _gym_out(row)


# Status --------------------------------------------------------------------------


def _facts(plan: BouncePlan | None, tz: str) -> rules.PlanFacts | None:
    if plan is None:
        return None
    return rules.PlanFacts(
        created_on=_local_date(plan.created_at, tz),
        based_on_checkin_day=plan.based_on_checkin_day,
        mode=plan.mode,
    )


async def _plans_left(session: AsyncSession, user: User) -> int:
    used = await bounce_repo.plans_since(session, user.id, _now() - timedelta(days=1))
    return max(0, get_settings().ai_daily_plan_limit - used)


def _inputs_changed(plan: BouncePlan, profile: Profile, gym: GymProfile | None) -> bool:
    """Profile, mode or gym details edited since the plan was written."""
    if plan.mode != profile.training_mode:
        return True
    if profile.updated_at and profile.updated_at > plan.created_at:
        return True
    return bool(gym and plan.mode != "activity" and gym.updated_at > plan.created_at)


_MESSAGES = {
    "disabled": "Bounce is switched off on this server. The admin can turn it on with an AI key.",
    "gym_needed": "Tell Bounce about your gym routine and any supplements to get your plan.",
    "none": "Ready when you are. Bounce will build your first week from your profile.",
    "active": "Your week is set. Follow today's part and log what you do.",
    "changed": "Your details changed. Bounce can rebuild this week's plan to match.",
    "checkin_needed": "A week is done. Log your weekly check-in so Bounce can update your plan.",
    "update_ready": "Check-in received. Bounce can build next week's plan now.",
}


async def status(session: AsyncSession, user: User, llm: LLMClient | None) -> BounceStatusOut:
    profile = await require_profile(session, user)
    today = local_today(profile.timezone)
    plan = await bounce_repo.latest_plan(session, user.id)
    gym = await bounce_repo.gym_profile(session, user.id)
    latest = await checkin_repo.latest(session, user.id)
    gym_needed = profile.training_mode != "activity" and gym is None

    if llm is None:
        state = "disabled"
    else:
        state = rules.plan_state(
            _facts(plan, profile.timezone), latest.day if latest else None, today
        )
    changed = state == "active" and plan is not None and _inputs_changed(plan, profile, gym)
    key = state
    if gym_needed and state in ("none", "active", "update_ready"):
        key = "gym_needed"
    elif changed:
        key = "changed"

    next_update = None
    if plan is not None:
        next_update = _local_date(plan.created_at, profile.timezone) + timedelta(
            days=rules.PLAN_DAYS
        )

    plans_left = await _plans_left(session, user) if llm else 0
    can_generate = (
        llm is not None
        and not gym_needed
        and plans_left > 0
        and (state in ("none", "update_ready") or changed)
    )
    return BounceStatusOut(
        enabled=llm is not None,
        mode=profile.training_mode,  # type: ignore[arg-type]
        state=state,  # type: ignore[arg-type]
        gym_profile_needed=gym_needed,
        plan_created_at=plan.created_at if plan else None,
        next_update_on=next_update,
        plans_left_today=plans_left,
        can_generate=can_generate,
        message=_MESSAGES[key],
        tips=await _tips(session, user, profile, today, plan, latest),
        notification=await _notification(session, user, profile, today, latest),
    )


async def _notification(
    session: AsyncSession, user: User, profile: Profile, today: date, latest_checkin
) -> BounceNotificationOut | None:
    row = await activity_repo.get(session, user.id, today)
    meals = await nutrition_repo.meals_on(session, user.id, today)
    nudge = rules.pick_nudge(
        today,
        datetime.now(ZoneInfo(profile.timezone)).hour,
        checkin_engine.checkin_due(latest_checkin.day if latest_checkin else None, today),
        {m.meal_type for m in meals if m.items},
        row.steps if row is not None else None,
        profile.daily_step_goal,
    )
    if nudge is None:
        return None
    return BounceNotificationOut(
        id=nudge.id,
        kind=nudge.kind,  # type: ignore[arg-type]
        title=nudge.title,
        message=nudge.message,
        action_label=nudge.action_label,
    )


async def _tips(
    session: AsyncSession,
    user: User,
    profile: Profile,
    today: date,
    plan: BouncePlan | None,
    latest_checkin,
) -> list[str]:
    """Immediate suggestions from today's numbers (rule based, no AI call)."""
    tips: list[str] = []
    row = await activity_repo.get(session, user.id, today)
    steps = row.steps if row and row.steps is not None else None
    goal = profile.daily_step_goal
    if steps is None:
        tips.append("Add today's steps so Bounce can see how your day is going.")
    elif steps < goal:
        left = goal - steps
        minutes = max(5, round(left / STEPS_PER_MINUTE / 5) * 5)
        tips.append(f"{left:,} steps to your goal. A brisk {minutes}-minute walk gets you there.")
    else:
        tips.append("Step goal done today. A few minutes of stretching will help you recover.")
    if checkin_engine.checkin_due(latest_checkin.day if latest_checkin else None, today):
        tips.append("Your weekly check-in is due. It is what lets your plan adapt.")
    if plan is not None:
        weekday = today.strftime("%a")
        content = PlanContent.model_validate(plan.content)
        day = next((d for d in content.days if d.day == weekday), None)
        if day is not None:
            tips.append(_today_line(day))
        tips += content.tips[: max(0, 4 - len(tips))]
    return tips[:4]


def _today_line(day) -> str:
    if day.rest:
        return "Today is a rest day in your plan. An easy walk still counts."
    parts = []
    if day.gym_exercises:
        parts.append(f"{day.gym_focus or 'gym'} session ({len(day.gym_exercises)} exercises)")
    if day.home_exercises:
        parts.append(f"{len(day.home_exercises)} home exercises")
    if day.walk_minutes:
        parts.append(f"{day.walk_minutes} min walk")
    if day.jog_minutes:
        parts.append(f"{day.jog_minutes} min jog")
    return "Today's plan: " + ", ".join(parts) + "." if parts else "Today's plan: keep moving."


# Plans ---------------------------------------------------------------------------


def _plan_out(row: BouncePlan) -> BouncePlanOut:
    return BouncePlanOut(
        id=row.id,
        created_at=row.created_at,
        week_start=row.week_start,
        mode=row.mode,  # type: ignore[arg-type]
        model=row.model,
        based_on_checkin_day=row.based_on_checkin_day,
        targets=Targets.model_validate(row.targets),
        content=PlanContent.model_validate(row.content),
    )


async def current_plan(session: AsyncSession, user: User) -> BouncePlanOut:
    row = await bounce_repo.latest_plan(session, user.id)
    if row is None:
        raise NotFoundError("Bounce has not made a plan for you yet.", code="no_plan")
    return _plan_out(row)


async def _targets(session: AsyncSession, user: User, profile: Profile, today: date) -> Targets:
    row = await nutrition_repo.target_for_day(session, user.id, today)
    if row is not None:
        return Targets(
            calories_kcal=row.calories_kcal,
            protein_g=row.protein_g,
            carbs_g=row.carbs_g,
            fat_g=row.fat_g,
        )
    t = breakdown(profile).targets
    return Targets(
        calories_kcal=t.calories_kcal, protein_g=t.protein_g, carbs_g=t.carbs_g, fat_g=t.fat_g
    )


async def _context(
    session: AsyncSession,
    user: User,
    profile: Profile,
    gym: GymProfile | None,
    targets: Targets,
    today: date,
    previous: BouncePlan | None,
) -> BounceContext:
    checkins = (await checkin_repo.list_all(session, user.id))[-4:]
    start = today - timedelta(days=6)
    days = await activity_repo.list_range(session, user.id, start, today)
    steps = [d.steps for d in days if d.steps is not None]
    sessions = await training_repo.sessions_between(session, user.id, start, today)
    return BounceContext(
        mode=profile.training_mode,
        age=profile.age,
        sex=profile.sex,
        height_cm=float(profile.height_cm),
        weight_kg=float(profile.weight_kg),
        goal=profile.goal,
        level=profile.level,
        minutes_per_day=profile.minutes_per_day,
        days_per_week=profile.days_per_week,
        diet_type=profile.diet_type,
        daily_step_goal=profile.daily_step_goal,
        calories_kcal=targets.calories_kcal,
        protein_g=targets.protein_g,
        carbs_g=targets.carbs_g,
        fat_g=targets.fat_g,
        gym=GymInfo(
            experience=gym.experience,
            days_per_week=gym.days_per_week,
            session_minutes=gym.session_minutes,
            supplements=list(gym.supplements or []),
            supplements_note=gym.supplements_note,
            injuries_note=gym.injuries_note,
        )
        if gym is not None and profile.training_mode != "activity"
        else None,
        life=_lifestyle(profile),
        checkins=[
            CheckinPoint(
                day=c.day.isoformat(),
                weight_kg=float(c.weight_kg),
                waist_cm=float(c.waist_cm) if c.waist_cm is not None else None,
            )
            for c in checkins
        ],
        avg_steps_7d=round(sum(steps) / len(steps)) if steps else None,
        step_goal_days_7d=sum(1 for s in steps if s >= profile.daily_step_goal),
        workouts_done_7d=sum(1 for s in sessions.values() if s.status == "done"),
        previous_summary=(previous.content or {}).get("summary") if previous else None,
    )


async def _ask(llm: LLMClient, ctx: BounceContext) -> PlanContent:
    """Ask the model, validate, and give it one chance to fix a bad reply."""
    reason: str | None = None
    for _ in range(2):
        try:
            text = await llm.complete(build_messages(ctx, reason), MAX_TOKENS)
        except LLMError as exc:
            raise UpstreamError(exc.message, code=exc.code) from exc
        try:
            content = PlanContent.model_validate(extract_json(text))
        except (ValueError, ValidationError) as exc:
            reason = f"it was not valid JSON in the required shape ({str(exc)[:300]})"
            log.warning("bounce: invalid model output")
            continue
        bad = rules.diet_violations(content, ctx.diet_type)
        if bad:
            reason = f"the meal plan includes {', '.join(bad)}, which this diet excludes"
            log.warning("bounce: diet type violated")
            continue
        return content
    raise UpstreamError(
        "Bounce could not write a usable plan this time. Try again in a moment.",
        code="model_bad_output",
    )


async def generate(session: AsyncSession, user: User, llm: LLMClient | None) -> BouncePlanOut:
    if llm is None:
        raise UnavailableError(_MESSAGES["disabled"], code="bounce_disabled")
    profile = await require_profile(session, user)
    today = local_today(profile.timezone)
    gym = await bounce_repo.gym_profile(session, user.id)
    if profile.training_mode != "activity" and gym is None:
        raise ConflictError(_MESSAGES["gym_needed"], code="gym_profile_needed")

    previous = await bounce_repo.latest_plan(session, user.id)
    latest = await checkin_repo.latest(session, user.id)
    state = rules.plan_state(
        _facts(previous, profile.timezone), latest.day if latest else None, today
    )
    if state == "checkin_needed":
        raise ConflictError(_MESSAGES["checkin_needed"], code="checkin_needed")
    if state == "active" and previous is not None and not _inputs_changed(previous, profile, gym):
        raise ConflictError(
            "Your plan for this week is already set. Change your profile or gym details to "
            "rebuild it, or wait for next week's check-in.",
            code="plan_current",
        )
    if await _plans_left(session, user) <= 0:
        raise RateLimitError("Bounce has made enough plans today. Try again tomorrow.")

    targets = await _targets(session, user, profile, today)
    ctx = await _context(session, user, profile, gym, targets, today, previous)
    content = await _ask(llm, ctx)
    supplements = list(gym.supplements or []) if gym and profile.training_mode != "activity" else []
    content = rules.finalize(content, profile.training_mode, supplements)

    row = BouncePlan(
        user_id=user.id,
        mode=profile.training_mode,
        week_start=_monday(today),
        content=content.model_dump(mode="json"),
        targets=targets.model_dump(),
        model=(getattr(llm, "last_model", None) or llm.model)[:120],
        based_on_checkin_day=latest.day if latest else None,
        created_at=_now(),
    )
    bounce_repo.add(session, row)
    await session.commit()
    return _plan_out(row)


WORK_WORDS = {
    "desk": "desk job, sits most of the day",
    "standing": "on their feet most of the day",
    "physical": "physical work",
    "shifts": "shift work with changing hours",
}
FOOD_FROM_WORDS = {
    "home": "home-cooked food",
    "hostel": "hostel or mess food",
    "out": "mostly eats out",
    "mixed": "a mix of home food and eating out",
}


def _lifestyle(profile: Profile) -> Lifestyle:
    """The "Know me" answers, in words the model can use. Only set fields are sent."""
    state = states_by_code().get(profile.state or "")
    by_code = foods_by_code()
    return Lifestyle(
        city=profile.city,
        state=state.name if state else None,
        region=state.region if state else None,
        work=WORK_WORDS.get(profile.work_type or ""),
        food_from=FOOD_FROM_WORDS.get(profile.food_source or ""),
        wake_time=profile.wake_time,
        usual_foods=[by_code[c].name for c in profile.usual_foods or () if c in by_code],
        sleep_hours=float(profile.sleep_hours) if profile.sleep_hours is not None else None,
        sweet_drinks_per_day=profile.sweet_drinks_per_day,
        fasting=profile.fasting_note,
        food_budget_inr_per_day=profile.food_budget_inr,
    )
