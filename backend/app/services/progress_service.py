"""Goal projection and then-vs-now progress cards."""

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timeutil import local_today
from app.engines import progress_engine as pe
from app.engines import projection_engine as proj
from app.models.user import User
from app.repositories import (
    activity_repo,
    checkin_repo,
    nutrition_repo,
    run_repo,
    training_repo,
)
from app.schemas.progress import (
    BlockOut,
    ChangeOut,
    ProgressCardOut,
    ProgressOut,
    ProjectionOut,
)
from app.services.common import require_profile
from app.services.nutrition_service import breakdown


def _f(v) -> float | None:
    return None if v is None else float(v)


def _block(b: pe.Block) -> BlockOut:
    return BlockOut(**b.__dict__)


def _changes(items: list[pe.Change]) -> list[ChangeOut]:
    return [ChangeOut(**c.__dict__) for c in items]


async def get(session: AsyncSession, user: User) -> ProgressOut:
    profile = await require_profile(session, user)
    today = local_today(profile.timezone)
    rows = await checkin_repo.list_all(session, user.id)

    # Projection from the calorie gap (or the real trend once there is enough data).
    target_row = await nutrition_repo.target_for_day(session, user.id, today)
    b = breakdown(profile)
    target_kcal = target_row.calories_kcal if target_row else b.targets.calories_kcal
    gap = b.maintenance - target_kcal
    current = float(profile.weight_kg)
    target = _f(profile.target_weight_kg)
    weigh_ins = [proj.WeighIn(r.day, float(r.weight_kg)) for r in rows]
    p = proj.project(current, target, gap, weigh_ins, today)
    recent = [w for w in weigh_ins if w.day >= today - timedelta(days=proj.TREND_WINDOW_DAYS)]
    projection = ProjectionOut(
        **p.__dict__,
        safe_rate_kg=round(proj.safe_rate(current, (target or current) < current), 2),
        daily_gap_kcal=gap,
        checkins_for_trend=max(0, proj.TREND_MIN_CHECKINS - len(recent)),
    )

    cards: list[ProgressCardOut] = []
    next_on = None
    if rows:
        first = rows[0].day
        next_on = pe.next_card_on(first, today)
        if pe.cards_ready(first, today):
            start = max(first, today - timedelta(days=pe.CARD_DAYS * (pe.MAX_CARDS + 1)))
            start -= timedelta(days=pe.CARD_DAYS)  # the block before the oldest card
            steps = {
                a.day: a.steps
                for a in await activity_repo.list_range(session, user.id, start, today)
                if a.steps is not None
            }
            sessions = await training_repo.sessions_between(session, user.id, start, today)
            log = pe.DailyLog(
                steps=steps,
                workout_days=frozenset(d for d, s in sessions.items() if s.status == "done"),
                run_m=await run_repo.metres_by_day(session, user.id, start, today),
                meal_days=frozenset(
                    await nutrition_repo.meal_types_by_day(session, user.id, start, today)
                ),
            )
            points = [
                pe.CheckinPoint(
                    day=r.day,
                    weight_kg=float(r.weight_kg),
                    waist_cm=_f(r.waist_cm),
                    chest_cm=_f(r.chest_cm),
                    arms_cm=_f(r.arms_cm),
                    thighs_cm=_f(r.thighs_cm),
                    energy=r.energy,
                    sleep=r.sleep,
                    stairs=r.stairs,
                )
                for r in rows
            ]
            for c in pe.build_cards(profile.goal, points, log, today):
                cards.append(
                    ProgressCardOut(
                        number=c.number,
                        start=c.start,
                        end=c.end,
                        then_day=c.then_day,
                        now_day=c.now_day,
                        measures=_changes(c.measures),
                        wins=_changes(c.wins),
                        block=_block(c.block),
                        previous_block=_block(c.previous_block) if c.previous_block else None,
                        highlights=c.highlights,
                    )
                )
    return ProgressOut(
        today=today, goal=profile.goal, projection=projection, cards=cards, next_card_on=next_on
    )
