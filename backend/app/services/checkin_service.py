"""Weekly check-ins: weight and measurements."""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFoundError
from app.core.timeutil import local_today
from app.engines import checkin_engine as eng
from app.models.checkin import Checkin
from app.models.user import User
from app.repositories import checkin_repo
from app.schemas.adjustment import CheckinSavedOut
from app.schemas.checkin import CheckinIn, CheckinOut, CheckinStatusOut
from app.services import adjustment_service, milestone_service
from app.services.common import require_profile


def _f(v) -> float | None:
    return None if v is None else float(v)


def _out(row: Checkin, previous: Checkin | None) -> CheckinOut:
    return CheckinOut(
        day=row.day,
        weight_kg=float(row.weight_kg),
        waist_cm=_f(row.waist_cm),
        chest_cm=_f(row.chest_cm),
        arms_cm=_f(row.arms_cm),
        thighs_cm=_f(row.thighs_cm),
        note=row.note,
        weight_change_kg=eng.change(
            _f(row.weight_kg), _f(previous.weight_kg) if previous else None
        ),
        waist_change_cm=eng.change(_f(row.waist_cm), _f(previous.waist_cm) if previous else None),
    )


async def list_checkins(session: AsyncSession, user: User) -> list[CheckinOut]:
    """Newest first, each with the change from the check-in before it."""
    rows = await checkin_repo.list_all(session, user.id)
    out = [_out(row, rows[i - 1] if i else None) for i, row in enumerate(rows)]
    return list(reversed(out))


async def status(session: AsyncSession, user: User) -> CheckinStatusOut:
    profile = await require_profile(session, user)
    today = local_today(profile.timezone)
    last = await checkin_repo.latest(session, user.id)
    return CheckinStatusOut(
        due=eng.checkin_due(last.day if last else None, today),
        last_day=last.day if last else None,
        days_since=(today - last.day).days if last else None,
        today=today,
    )


async def save(session: AsyncSession, user: User, day: date, data: CheckinIn) -> CheckinSavedOut:
    profile = await require_profile(session, user)
    if day > local_today(profile.timezone):
        raise AppError("You cannot check in for a future day.", code="future_day")
    row = await checkin_repo.get(session, user.id, day)
    if row is None:
        row = Checkin(user_id=user.id, day=day)
        checkin_repo.add(session, row)
    row.weight_kg = data.weight_kg
    row.waist_cm, row.chest_cm = data.waist_cm, data.chest_cm
    row.arms_cm, row.thighs_cm = data.arms_cm, data.thighs_cm
    row.note = data.note
    await session.flush()

    latest = await checkin_repo.latest(session, user.id)
    if latest is not None and latest.day == day:
        # The newest check-in is the user's current weight.
        profile.weight_kg = data.weight_kg
    await session.flush()
    adjustment, note = await adjustment_service.maybe_adjust(session, user, profile, day)
    await milestone_service.evaluate(session, user.id)
    await session.commit()

    rows = await checkin_repo.list_all(session, user.id)
    i = next(i for i, r in enumerate(rows) if r.day == day)
    out = _out(rows[i], rows[i - 1] if i else None)
    return CheckinSavedOut(**out.model_dump(), adjustment=adjustment, adjustment_note=note)


async def delete(session: AsyncSession, user: User, day: date) -> None:
    if not await checkin_repo.remove(session, user.id, day):
        raise NotFoundError("No check-in on this day.", code="checkin_missing")
    await milestone_service.evaluate(session, user.id)
    await session.commit()
