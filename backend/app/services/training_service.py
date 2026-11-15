"""Training plans (weekly, rule-based) and workout logging."""

from dataclasses import asdict
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.content import exercise_library
from app.core.errors import AppError, NotFoundError
from app.core.security import utcnow
from app.core.timeutil import local_today
from app.engines import training_engine as eng
from app.models.profile import Profile
from app.models.training import TrainingPlan, WorkoutSession, WorkoutSet
from app.models.user import User
from app.repositories import training_repo
from app.schemas.training import (
    DayStatus,
    DrillOut,
    ExerciseOut,
    PlanDayOut,
    PlannedSessionOut,
    PrescriptionOut,
    SetOut,
    WeekOut,
    WorkoutBrief,
    WorkoutIn,
    WorkoutOut,
    WorkoutSummaryOut,
)
from app.services import milestone_service
from app.services.common import require_profile

PLAN_FIELDS = ("goal", "level", "minutes_per_day", "days_per_week", "has_pullup_bar")


def week_start_for(day: date) -> date:
    return day - timedelta(days=day.weekday())


def training_input(profile: Profile) -> eng.TrainingInput:
    return eng.TrainingInput(
        goal=profile.goal,
        level=profile.level,
        minutes_per_day=profile.minutes_per_day,
        days_per_week=profile.days_per_week,
        has_pullup_bar=profile.has_pullup_bar,
    )


# plan_json <-> engine dataclasses -------------------------------------------


def _session_to_json(s: eng.SessionPlan) -> dict:
    return {
        "day_offset": s.day_offset,
        "kind": s.kind,
        "title": s.title,
        "focus": list(s.focus),
        "warmup": list(s.warmup),
        "exercises": [asdict(p) for p in s.exercises],
        "finisher": asdict(s.finisher) if s.finisher else None,
        "cooldown": list(s.cooldown),
        "est_minutes": s.est_minutes,
    }


def _session_from_json(d: dict) -> eng.SessionPlan:
    return eng.SessionPlan(
        day_offset=d["day_offset"],
        kind=d["kind"],
        title=d["title"],
        focus=tuple(d["focus"]),
        warmup=tuple(d["warmup"]),
        exercises=tuple(eng.Prescription(**p) for p in d["exercises"]),
        finisher=eng.Prescription(**d["finisher"]) if d.get("finisher") else None,
        cooldown=tuple(d["cooldown"]),
        est_minutes=d["est_minutes"],
    )


def _plan_json(split: str, sessions: list[dict], profile: Profile) -> dict:
    return {
        "version": 1,
        "split": split,
        "inputs": {f: getattr(profile, f) for f in PLAN_FIELDS},
        "sessions": sessions,
    }


def _build(profile: Profile) -> eng.WeekPlan:
    lib = exercise_library()
    return eng.build_week(training_input(profile), lib.exercises, lib.warmup, lib.cooldown)


def _sessions_by_day(plan: TrainingPlan) -> dict[date, eng.SessionPlan]:
    out = {}
    for d in plan.plan_json["sessions"]:
        s = _session_from_json(d)
        out[plan.week_start + timedelta(days=s.day_offset)] = s
    return out


# Plan lifecycle --------------------------------------------------------------


async def ensure_plan(
    session: AsyncSession, user: User, profile: Profile, week_start: date
) -> TrainingPlan:
    """The current plan for a week, generated from the profile if there is none yet.
    Flushes but does not commit."""
    row = await training_repo.latest_plan(session, user.id, week_start)
    if row is not None:
        return row
    week = _build(profile)
    row = TrainingPlan(
        user_id=user.id,
        week_start=week_start,
        plan_json=_plan_json(week.split, [_session_to_json(s) for s in week.sessions], profile),
    )
    training_repo.add(session, row)
    await session.flush()
    return row


async def regenerate_from_tomorrow(session: AsyncSession, user: User, profile: Profile) -> None:
    """After a goal, level, time, days or pull-up bar change: keep this week's sessions up
    to today as they were, and use the new plan from tomorrow. Does not commit."""
    today = local_today(profile.timezone)
    week_start = week_start_for(today)
    current = await training_repo.latest_plan(session, user.id, week_start)
    new = _build(profile)
    kept = []
    if current is not None:
        kept = [
            d
            for d in current.plan_json["sessions"]
            if week_start + timedelta(days=d["day_offset"]) <= today
        ]
    added = [
        _session_to_json(s)
        for s in new.sessions
        if week_start + timedelta(days=s.day_offset) > today
    ]
    training_repo.add(
        session,
        TrainingPlan(
            user_id=user.id,
            week_start=week_start,
            plan_json=_plan_json(new.split, kept + added, profile),
        ),
    )
    await session.flush()


# Output helpers ----------------------------------------------------------------


def _prescription_out(p: eng.Prescription) -> PrescriptionOut:
    ex = exercise_library().by_code().get(p.code)
    return PrescriptionOut(
        code=p.code,
        name=ex.name if ex else p.code,
        group=ex.group if ex else "core",
        type=ex.type if ex else ("timed" if p.target_seconds is not None else "reps"),
        sets=p.sets,
        rest_s=p.rest_s,
        reps_min=p.reps_min,
        reps_max=p.reps_max,
        target_reps=p.target_reps,
        seconds_min=p.seconds_min,
        seconds_max=p.seconds_max,
        target_seconds=p.target_seconds,
    )


def _drills_out(codes: tuple[str, ...]) -> list[DrillOut]:
    lib = exercise_library()
    out = []
    for c in codes:
        d = lib.drill(c)
        if d:
            out.append(
                DrillOut(code=d.code, name=d.name, seconds=d.seconds, instructions=d.instructions)
            )
    return out


def _session_out(day: date, s: eng.SessionPlan) -> PlannedSessionOut:
    return PlannedSessionOut(
        day=day,
        kind=s.kind,
        title=s.title,
        focus=list(s.focus),
        warmup=_drills_out(s.warmup),
        exercises=[_prescription_out(p) for p in s.exercises],
        finisher=_prescription_out(s.finisher) if s.finisher else None,
        cooldown=_drills_out(s.cooldown),
        est_minutes=s.est_minutes,
    )


def _status(day: date, today: date, planned: bool, logged: WorkoutSession | None) -> DayStatus:
    if logged is not None:
        return "done" if logged.status == "done" else "skipped"
    if not planned:
        return "rest"
    return "planned" if day >= today else "not_logged"


def _logged(row: WorkoutSession) -> list[eng.LoggedSet]:
    return [
        eng.LoggedSet(
            s.exercise_code,
            s.set_no,
            s.target_reps,
            s.actual_reps,
            s.target_seconds,
            s.actual_seconds,
        )
        for s in row.sets
    ]


def _workout_out(row: WorkoutSession) -> WorkoutOut:
    logged = _logged(row)
    return WorkoutOut(
        day=row.day,
        status=row.status,  # type: ignore[arg-type]
        finished_at=row.finished_at,
        sets=[
            SetOut(
                exercise_code=s.exercise_code,
                set_no=s.set_no,
                target_reps=s.target_reps,
                actual_reps=s.actual_reps,
                target_seconds=s.target_seconds,
                actual_seconds=s.actual_seconds,
                target_met=s.target_met,
            )
            for s in logged
        ],
        summary=WorkoutSummaryOut(**asdict(eng.summarize(logged))),
    )


# Public service functions --------------------------------------------------------


def list_exercises() -> list[ExerciseOut]:
    return [ExerciseOut(**asdict(e)) for e in exercise_library().exercises]


def get_exercise(code: str) -> ExerciseOut:
    ex = exercise_library().by_code().get(code)
    if ex is None:
        raise NotFoundError("Exercise not found.", code="exercise_missing")
    return ExerciseOut(**asdict(ex))


async def get_week(session: AsyncSession, user: User, day: date | None) -> WeekOut:
    profile = await require_profile(session, user)
    today = local_today(profile.timezone)
    week_start = week_start_for(day or today)
    if week_start > week_start_for(today):
        raise AppError(
            "Plans are made one week at a time. Future weeks are not ready yet.", code="future_week"
        )
    plan = await ensure_plan(session, user, profile, week_start)
    await session.commit()
    planned = _sessions_by_day(plan)
    logged = await training_repo.sessions_between(
        session, user.id, week_start, week_start + timedelta(days=6)
    )
    days = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        s = planned.get(d)
        days.append(
            PlanDayOut(
                day=d,
                status=_status(d, today, s is not None, logged.get(d)),
                session=_session_out(d, s) if s else None,
            )
        )
    return WeekOut(week_start=week_start, today=today, split=plan.plan_json["split"], days=days)


async def _planned_for(
    session: AsyncSession, user: User, profile: Profile, day: date
) -> tuple[TrainingPlan, eng.SessionPlan]:
    plan = await ensure_plan(session, user, profile, week_start_for(day))
    planned = _sessions_by_day(plan).get(day)
    if planned is None:
        raise AppError("This is a rest day in your plan.", code="rest_day")
    return plan, planned


async def get_workout(session: AsyncSession, user: User, day: date) -> WorkoutOut:
    row = await training_repo.get_session(session, user.id, day)
    if row is None:
        raise NotFoundError("No workout logged for this day.", code="workout_missing")
    return _workout_out(row)


async def save_workout(session: AsyncSession, user: User, day: date, data: WorkoutIn) -> WorkoutOut:
    profile = await require_profile(session, user)
    today = local_today(profile.timezone)
    if day > today:
        raise AppError("You cannot log a workout for a future day.", code="future_day")
    if week_start_for(day) > week_start_for(today):
        raise AppError("You cannot log a workout for a future week.", code="future_week")
    plan, planned = await _planned_for(session, user, profile, day)

    prescriptions = {p.code: p for p in planned.all_prescriptions}
    sent: dict[tuple[str, int], tuple[int | None, int | None]] = {}
    for s in data.sets:
        p = prescriptions.get(s.exercise_code)
        if p is None:
            raise AppError(f"{s.exercise_code} is not in this day's plan.", code="not_in_plan")
        if s.set_no > p.sets:
            raise AppError(f"{s.exercise_code} has only {p.sets} sets.", code="bad_set")
        key = (s.exercise_code, s.set_no)
        if key in sent:
            raise AppError("The same set was sent twice.", code="duplicate_set")
        sent[key] = (s.actual_reps, s.actual_seconds)

    row = await training_repo.get_session(session, user.id, day)
    if row is None:
        row = WorkoutSession(user_id=user.id, day=day)
        training_repo.add(session, row)
    row.plan_id = plan.id
    row.status = data.status
    row.finished_at = utcnow()
    row.sets = []
    if data.status == "done":
        # Every planned set is stored; sets not sent are "not done".
        for p in planned.all_prescriptions:
            for n in range(1, p.sets + 1):
                reps, secs = sent.get((p.code, n), (None, None))
                row.sets.append(
                    WorkoutSet(
                        exercise_code=p.code,
                        set_no=n,
                        target_reps=p.target_reps,
                        target_seconds=p.target_seconds,
                        actual_reps=reps if p.target_reps is not None else None,
                        actual_seconds=secs if p.target_seconds is not None else None,
                    )
                )
    await session.flush()
    await milestone_service.evaluate(session, user.id)
    await session.commit()
    return await get_workout(session, user, day)


async def delete_workout(session: AsyncSession, user: User, day: date) -> None:
    if not await training_repo.remove_session(session, user.id, day):
        raise NotFoundError("No workout logged for this day.", code="workout_missing")
    await milestone_service.evaluate(session, user.id)
    await session.commit()


async def today_brief(
    session: AsyncSession, user: User, profile: Profile, today: date
) -> WorkoutBrief | None:
    """Today's planned session for the Today screen, or None on a rest day. Does not commit."""
    plan = await ensure_plan(session, user, profile, week_start_for(today))
    planned = _sessions_by_day(plan).get(today)
    if planned is None:
        return None
    logged = await training_repo.sessions_between(session, user.id, today, today)
    return WorkoutBrief(
        day=today,
        title=planned.title,
        exercise_count=len(planned.exercises),
        est_minutes=planned.est_minutes,
        status=_status(today, today, True, logged.get(today)),
    )
