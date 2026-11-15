"""Runs: manual entry, GPX upload, list, detail, edit and delete."""

from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFoundError
from app.core.timeutil import local_today
from app.engines import run_engine as eng
from app.models.enums import Source
from app.models.profile import Profile
from app.models.run import Run, RunPoint
from app.models.user import User
from app.repositories import run_repo
from app.schemas.run import (
    RunDetailOut,
    RunIn,
    RunListOut,
    RunOut,
    RunPatch,
    SplitOut,
    TrackPointOut,
)
from app.services import gpx, milestone_service
from app.services.common import require_profile


def _out(run: Run, has_track: bool) -> RunOut:
    return RunOut(
        id=run.id,
        day=run.day,
        started_at=run.started_at,
        distance_m=run.distance_m,
        duration_s=run.duration_s,
        pace_s_per_km=eng.pace_s_per_km(run.distance_m, run.duration_s),
        calories_kcal=run.calories_kcal,
        source=Source(run.source),
        note=run.note,
        has_track=has_track,
        created_at=run.created_at,
    )


def _detail(run: Run) -> RunDetailOut:
    points = [eng.TrackPoint(p.lat, p.lng, p.ele_m, p.recorded_at) for p in run.points]
    splits = eng.splits(points, run.distance_m) if points else []
    return RunDetailOut(
        **_out(run, bool(points)).model_dump(),
        splits=[SplitOut(**s.__dict__) for s in splits],
        track=[TrackPointOut(lat=p.lat, lng=p.lng, ele_m=p.ele_m) for p in run.points],
    )


def _check_day(profile: Profile, day) -> None:
    if day > local_today(profile.timezone):
        raise AppError("You cannot log a run in the future.", code="future_day")


def _calories(profile: Profile, distance_m: int) -> int:
    return eng.calories_kcal(float(profile.weight_kg), distance_m)


async def list_runs(session: AsyncSession, user: User, limit: int, offset: int) -> RunListOut:
    rows, total = await run_repo.list_for_user(session, user.id, limit, offset)
    return RunListOut(items=[_out(r, t) for r, t in rows], total=total)


async def get_run(session: AsyncSession, user: User, run_id: int) -> RunDetailOut:
    run = await run_repo.get(session, user.id, run_id, with_points=True)
    if run is None:
        raise NotFoundError("Run not found.", code="run_missing")
    return _detail(run)


async def create_manual(session: AsyncSession, user: User, data: RunIn) -> RunDetailOut:
    profile = await require_profile(session, user)
    _check_day(profile, data.day)
    run = Run(
        user_id=user.id,
        day=data.day,
        distance_m=data.distance_m,
        duration_s=data.duration_s,
        calories_kcal=_calories(profile, data.distance_m),
        source=Source.manual.value,
        note=data.note,
    )
    run_repo.add(session, run)
    await milestone_service.evaluate(session, user.id)
    await session.commit()
    return await get_run(session, user, run.id)


async def create_from_gpx(
    session: AsyncSession, user: User, content: bytes, note: str | None
) -> RunDetailOut:
    profile = await require_profile(session, user)
    try:
        points = gpx.parse_gpx(content)
        stats = eng.track_stats(points)
    except (gpx.GpxError, ValueError) as exc:
        raise AppError(str(exc), code="gpx_invalid") from exc
    if stats.distance_m < 10 or stats.duration_s < 30:
        raise AppError("This track is too short to save as a run.", code="gpx_invalid")
    day = stats.started_at.astimezone(ZoneInfo(profile.timezone)).date()
    _check_day(profile, day)
    run = Run(
        user_id=user.id,
        day=day,
        started_at=stats.started_at,
        distance_m=stats.distance_m,
        duration_s=stats.duration_s,
        calories_kcal=_calories(profile, stats.distance_m),
        source=Source.gpx.value,
        note=(note or "").strip()[:500] or None,
        points=[
            RunPoint(seq=i, lat=p.lat, lng=p.lng, ele_m=p.ele_m, recorded_at=p.time)
            for i, p in enumerate(eng.downsample(points))
        ],
    )
    run_repo.add(session, run)
    await milestone_service.evaluate(session, user.id)
    await session.commit()
    return await get_run(session, user, run.id)


async def update_run(
    session: AsyncSession, user: User, run_id: int, data: RunPatch
) -> RunDetailOut:
    profile = await require_profile(session, user)
    run = await run_repo.get(session, user.id, run_id)
    if run is None:
        raise NotFoundError("Run not found.", code="run_missing")
    sent = data.model_fields_set
    if "day" in sent and data.day is not None:
        _check_day(profile, data.day)
        run.day = data.day
    if "distance_m" in sent and data.distance_m is not None:
        run.distance_m = data.distance_m
        run.calories_kcal = _calories(profile, data.distance_m)
    if "duration_s" in sent and data.duration_s is not None:
        run.duration_s = data.duration_s
    if "note" in sent:
        run.note = data.note
    await milestone_service.evaluate(session, user.id)
    await session.commit()
    return await get_run(session, user, run_id)


async def delete_run(session: AsyncSession, user: User, run_id: int) -> None:
    run = await run_repo.get(session, user.id, run_id)
    if run is None:
        raise NotFoundError("Run not found.", code="run_missing")
    await run_repo.delete(session, run)
    await milestone_service.evaluate(session, user.id)
    await session.commit()
