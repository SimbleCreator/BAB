"""Daily activity: entry, editing, summary and CSV import."""

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFoundError
from app.core.timeutil import local_today
from app.engines import activity_engine as eng
from app.models.activity import DailyActivity
from app.models.enums import Source
from app.models.profile import Profile
from app.models.user import User
from app.repositories import activity_repo
from app.schemas.activity import (
    ActivityIn,
    ActivityOut,
    ActivitySummaryOut,
    CsvImportOut,
    CsvPreviewOut,
    CsvRowOut,
    DayPoint,
)
from app.services import activity_csv, milestone_service
from app.services.common import require_profile

MAX_RANGE_DAYS = 366


def _body(profile: Profile) -> eng.BodyStats:
    return eng.BodyStats(height_cm=float(profile.height_cm), weight_kg=float(profile.weight_kg))


def to_out(row: DailyActivity, profile: Profile) -> ActivityOut:
    v = eng.resolve(eng.ActivityInput(row.steps, row.distance_m, row.active_kcal), _body(profile))
    return ActivityOut(
        day=row.day,
        steps=v.steps,
        distance_m=v.distance_m,
        active_kcal=v.active_kcal,
        distance_estimated=v.distance_estimated,
        active_kcal_estimated=v.active_kcal_estimated,
        source=Source(row.source),
        note=row.note,
        updated_at=row.updated_at,
    )


def _check_not_future(day: date, profile: Profile) -> None:
    if day > local_today(profile.timezone):
        raise AppError("You cannot log a day in the future.", code="future_day")


async def list_days(session: AsyncSession, user: User, start: date, end: date) -> list[ActivityOut]:
    profile = await require_profile(session, user)
    if end < start:
        raise AppError("The end date is before the start date.", code="bad_range")
    if (end - start).days >= MAX_RANGE_DAYS:
        raise AppError(f"Ask for at most {MAX_RANGE_DAYS} days at once.", code="bad_range")
    rows = await activity_repo.list_range(session, user.id, start, end)
    return [to_out(r, profile) for r in rows]


async def get_day(session: AsyncSession, user: User, day: date) -> ActivityOut:
    profile = await require_profile(session, user)
    row = await activity_repo.get(session, user.id, day)
    if row is None:
        raise NotFoundError("Nothing logged for this day.", code="activity_missing")
    return to_out(row, profile)


async def save_day(session: AsyncSession, user: User, day: date, data: ActivityIn) -> ActivityOut:
    profile = await require_profile(session, user)
    _check_not_future(day, profile)
    row = await activity_repo.get(session, user.id, day)
    if row is None:
        row = DailyActivity(user_id=user.id, day=day)
        activity_repo.add(session, row)
    row.steps, row.distance_m, row.active_kcal = data.steps, data.distance_m, data.active_kcal
    row.note = data.note
    row.source = Source.manual.value
    await milestone_service.evaluate(session, user.id)
    await session.commit()
    await session.refresh(row)
    return to_out(row, profile)


async def delete_day(session: AsyncSession, user: User, day: date) -> None:
    if not await activity_repo.remove(session, user.id, day):
        raise NotFoundError("Nothing logged for this day.", code="activity_missing")
    await milestone_service.evaluate(session, user.id)
    await session.commit()


async def summary(session: AsyncSession, user: User, days: int) -> ActivitySummaryOut:
    profile = await require_profile(session, user)
    today = local_today(profile.timezone)
    start = today - timedelta(days=days - 1)
    rows = {r.day: r for r in await activity_repo.list_range(session, user.id, start, today)}
    goal_days = await activity_repo.goal_days(session, user.id, profile.daily_step_goal)

    points: list[DayPoint] = []
    for i in range(days):
        day = start + timedelta(days=i)
        row = rows.get(day)
        if row is None:
            points.append(
                DayPoint(
                    day=day, has_entry=False, steps=0, distance_m=0, active_kcal=0, goal_met=False
                )
            )
            continue
        out = to_out(row, profile)
        points.append(
            DayPoint(
                day=day,
                has_entry=True,
                steps=out.steps or 0,
                distance_m=out.distance_m or 0,
                active_kcal=out.active_kcal or 0,
                goal_met=eng.goal_met(out.steps, profile.daily_step_goal),
            )
        )
    return ActivitySummaryOut(
        today=today,
        step_goal=profile.daily_step_goal,
        current_streak=eng.current_streak(goal_days, today),
        longest_streak=eng.longest_streak(goal_days),
        total_steps=sum(p.steps for p in points),
        total_distance_m=sum(p.distance_m for p in points),
        days=points,
    )


async def csv_preview(session: AsyncSession, user: User, content: bytes) -> CsvPreviewOut:
    profile = await require_profile(session, user)
    parsed = activity_csv.parse(content, local_today(profile.timezone))
    existing = await activity_repo.by_days(
        session, user.id, (r.day for r in parsed.rows if r.day is not None)
    )
    rows = [
        CsvRowOut(
            line=r.line,
            day=r.day,
            steps=r.steps,
            distance_m=r.distance_m,
            active_kcal=r.active_kcal,
            errors=r.errors,
            exists=r.day in existing,
        )
        for r in parsed.rows
    ]
    return CsvPreviewOut(
        file_errors=parsed.file_errors,
        rows=rows,
        valid_rows=sum(1 for r in rows if not r.errors),
        invalid_rows=sum(1 for r in rows if r.errors),
        existing_rows=sum(1 for r in rows if r.exists and not r.errors),
    )


async def csv_import(
    session: AsyncSession, user: User, content: bytes, overwrite: bool
) -> CsvImportOut:
    profile = await require_profile(session, user)
    parsed = activity_csv.parse(content, local_today(profile.timezone))
    if parsed.file_errors and not parsed.rows:
        raise AppError(parsed.file_errors[0], code="csv_invalid")
    valid = parsed.valid
    existing = await activity_repo.by_days(session, user.id, (r.day for r in valid))
    created = updated = skipped = 0
    for r in valid:
        assert r.day is not None  # noqa: S101 - valid rows always have a day
        row = existing.get(r.day)
        if row is not None and not overwrite:
            skipped += 1
            continue
        if row is None:
            row = DailyActivity(user_id=user.id, day=r.day)
            activity_repo.add(session, row)
            created += 1
        else:
            updated += 1
        row.steps, row.distance_m, row.active_kcal = r.steps, r.distance_m, r.active_kcal
        row.source = Source.csv.value
    await milestone_service.evaluate(session, user.id)
    await session.commit()
    return CsvImportOut(
        created=created,
        updated=updated,
        skipped_existing=skipped,
        skipped_invalid=len(parsed.rows) - len(valid),
    )
