"""Letter from future you: Bounce writes it once, it stays sealed for 90 days, then opens
beside the user's real progress."""

import logging
from datetime import date, timedelta

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, UnavailableError, UpstreamError
from app.core.security import utcnow
from app.core.timeutil import local_today
from app.engines import projection_engine
from app.models.bounce import BounceLetter
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
    LetterBody,
    LetterOut,
    LetterStatusOut,
    PlanContent,
    SnapshotOut,
)
from app.services.bounce import letter_rules as lr
from app.services.bounce.llm import LLMClient, LLMError, extract_json
from app.services.bounce.prompt import LetterContext, build_letter_messages
from app.services.bounce.service import _lifestyle
from app.services.common import require_profile
from app.services.nutrition_service import breakdown

log = logging.getLogger(__name__)
LETTER_MAX_TOKENS = 1200
SIGN_OFF = "You, 90 days from now"
DIET_WORDS = {"veg": "vegetarian", "egg": "vegetarian with eggs", "non_veg": "non-vegetarian"}
TRAINING_WORDS = {
    "activity": "walking, jogging and home workouts",
    "gym": "gym training",
    "both": "gym days and walking or home days",
}


def _f(v) -> float | None:
    return None if v is None else float(v)


async def _snapshot(session: AsyncSession, user: User, profile: Profile, today: date) -> dict:
    start7, start28 = today - timedelta(days=6), today - timedelta(days=27)
    steps = [
        a.steps
        for a in await activity_repo.list_range(session, user.id, start7, today)
        if a.steps is not None
    ]
    sessions = await training_repo.sessions_between(session, user.id, start28, today)
    meals = await nutrition_repo.meal_types_by_day(session, user.id, start28, today)
    last = await checkin_repo.latest(session, user.id)
    snap = lr.Snapshot(
        weight_kg=float(profile.weight_kg),
        target_weight_kg=_f(profile.target_weight_kg),
        waist_cm=_f(last.waist_cm) if last else None,
        avg_steps_7d=round(sum(steps) / len(steps)) if steps else None,
        workouts_28d=sum(1 for s in sessions.values() if s.status == "done"),
        meal_days_28d=len(meals),
        step_goal=profile.daily_step_goal,
    )
    return snap.__dict__


def _letter_out(row: BounceLetter, profile: Profile) -> LetterOut:
    return LetterOut(
        written_on=row.written_on,
        open_on=row.open_on,
        greeting=f"Dear {profile.name},",
        paragraphs=list(row.content.get("paragraphs", [])),
        sign_off=SIGN_OFF,
        opened_at=row.opened_at,
    )


async def status(session: AsyncSession, user: User, llm: LLMClient | None) -> LetterStatusOut:
    profile = await require_profile(session, user)
    today = local_today(profile.timezone)
    row = await bounce_repo.latest_letter(session, user.id)
    st = lr.state(row.written_on if row else None, bool(row and row.opened_at), today)
    opened = row is not None and st == "opened"
    return LetterStatusOut(
        enabled=llm is not None,
        state=st,
        today=today,
        written_on=row.written_on if row else None,
        open_on=row.open_on if row else None,
        days_left=max(0, (row.open_on - today).days) if row and st == "sealed" else None,
        can_write=llm is not None and st in ("none", "opened"),
        letter=_letter_out(row, profile) if opened and row else None,
        then=SnapshotOut(**row.snapshot) if opened and row else None,
        now=SnapshotOut(**await _snapshot(session, user, profile, today)) if opened else None,
    )


async def _context(
    session: AsyncSession, user: User, profile: Profile, today: date, snap: dict
) -> LetterContext:
    target = _f(profile.target_weight_kg)
    direction = None
    weeks = None
    if target is not None and abs(target - float(profile.weight_kg)) > 0.3:
        direction = "lower" if target < float(profile.weight_kg) else "higher"
        b = breakdown(profile)
        row = await nutrition_repo.target_for_day(session, user.id, today)
        gap = b.maintenance - (row.calories_kcal if row else b.targets.calories_kcal)
        p = projection_engine.project(float(profile.weight_kg), target, gap, [], today)
        if p.status == "on_track":
            weeks = f"{p.weeks_min} to {p.weeks_max} weeks"
    plan = await bounce_repo.latest_plan(session, user.id)
    summary = None
    if plan is not None:
        try:
            summary = PlanContent.model_validate(plan.content).summary
        except ValidationError:
            summary = None
    return LetterContext(
        goal=profile.goal,
        training=TRAINING_WORDS.get(profile.training_mode, profile.training_mode),
        level=profile.level,
        days_per_week=profile.days_per_week,
        minutes_per_day=profile.minutes_per_day,
        daily_step_goal=profile.daily_step_goal,
        diet=DIET_WORDS.get(profile.diet_type, profile.diet_type),
        target_direction=direction,
        weeks_estimate=weeks,
        plan_summary=summary,
        avg_steps_7d=snap["avg_steps_7d"],
        life=_lifestyle(profile),
    )


async def _ask(llm: LLMClient, ctx: LetterContext) -> list[str]:
    reason: str | None = None
    for _ in range(2):
        try:
            text = await llm.complete(build_letter_messages(ctx, reason), LETTER_MAX_TOKENS)
        except LLMError as exc:
            raise UpstreamError(exc.message, code=exc.code) from exc
        try:
            body = LetterBody.model_validate(extract_json(text))
        except (ValueError, ValidationError) as exc:
            reason = "it was not a JSON object with a list of paragraphs"
            log.warning("bounce letter: invalid model output (%s)", type(exc).__name__)
            continue
        paragraphs = lr.clean(body.paragraphs)
        why = lr.problem(paragraphs)
        if why is None:
            return paragraphs
        reason = f"{why}, after removing sentences that named weights or made promises"
        log.warning(
            "bounce letter: unusable after cleaning (%s; model %s)",
            why,
            getattr(llm, "last_model", None),
        )
    raise UpstreamError(
        "Bounce could not write your letter this time. Try again in a moment.",
        code="model_bad_output",
    )


async def write(session: AsyncSession, user: User, llm: LLMClient | None) -> LetterStatusOut:
    """Write a new letter. Only when there is none, or the last one has been opened."""
    if llm is None:
        raise UnavailableError("Bounce is switched off.", code="bounce_disabled")
    profile = await require_profile(session, user)
    today = local_today(profile.timezone)
    row = await bounce_repo.latest_letter(session, user.id)
    st = lr.state(row.written_on if row else None, bool(row and row.opened_at), today)
    if st in ("sealed", "ready"):
        raise ConflictError(
            "You already have a sealed letter. Open it on its day first.", code="letter_sealed"
        )
    snap = await _snapshot(session, user, profile, today)
    paragraphs = await _ask(llm, await _context(session, user, profile, today, snap))
    bounce_repo.add(
        session,
        BounceLetter(
            user_id=user.id,
            written_on=today,
            open_on=lr.open_on(today),
            content={"paragraphs": paragraphs},
            snapshot=snap,
            model=(getattr(llm, "last_model", None) or llm.model)[:120],
        ),
    )
    await session.commit()
    return await status(session, user, llm)


async def open_letter(session: AsyncSession, user: User, llm: LLMClient | None) -> LetterStatusOut:
    profile = await require_profile(session, user)
    today = local_today(profile.timezone)
    row = await bounce_repo.latest_letter(session, user.id)
    if row is None:
        raise NotFoundError("No letter yet.", code="letter_missing")
    if row.opened_at is None:
        if today < row.open_on:
            raise ConflictError(
                f"Your letter opens on {row.open_on.isoformat()}.", code="letter_not_ready"
            )
        row.opened_at = utcnow()
        await session.commit()
    return await status(session, user, llm)
