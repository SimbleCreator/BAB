from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.timeutil import local_today
from app.models import TrainingPlan
from tests.helpers import PROFILE, onboard

pytestmark = pytest.mark.anyio

TZ = PROFILE["timezone"]  # female, 64.5 kg, lose fat, 3 days; starting target 1687 kcal


def day(n: int) -> str:
    return str(local_today(TZ) - timedelta(days=n))


async def checkin(client, h, n: int, kg: float) -> dict:
    r = await client.put(f"/api/v1/checkins/{day(n)}", json={"weight_kg": kg}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


async def target(client, h) -> dict:
    return (await client.get("/api/v1/nutrition/targets", headers=h)).json()["current"]


async def test_first_checkin_only_sets_a_starting_point(client):
    h = await onboard(client)
    r = await checkin(client, h, 7, 64.5)
    assert r["adjustment"] is None
    assert "starting point" in r["adjustment_note"]


async def test_slow_loss_lowers_calories_by_100(client):
    h = await onboard(client)
    await checkin(client, h, 7, 64.5)
    r = await checkin(client, h, 0, 64.4)  # -0.16% in a week, under 0.25%
    a = r["adjustment"]
    assert a["nutrition"] == {
        "before_kcal": 1687,
        "after_kcal": 1587,
        "change_kcal": -100,
        "floor_applied": False,
        "reason": a["nutrition"]["reason"],
    }
    assert a["weekly_change_pct"] == pytest.approx(-0.16, abs=0.01)
    assert a["reference_day"] == day(7)
    t = await target(client, h)
    assert t["calories_kcal"] == 1587
    assert t["reason"].startswith("Weekly check-in")
    assert t["protein_g"] == round(1.8 * 64.4)
    listed = (await client.get("/api/v1/checkins/adjustments", headers=h)).json()
    assert len(listed) == 1 and listed[0]["summary"]


async def test_fast_loss_raises_calories_by_150(client):
    h = await onboard(client)
    await checkin(client, h, 7, 66.0)
    r = await checkin(client, h, 0, 65.0)  # -1.5%
    assert r["adjustment"]["nutrition"]["change_kcal"] == 150


async def test_on_track_keeps_calories(client):
    h = await onboard(client)
    await checkin(client, h, 7, 66.0)
    r = await checkin(client, h, 0, 65.6)  # -0.6%
    assert r["adjustment"]["nutrition"]["change_kcal"] == 0
    assert (await target(client, h))["calories_kcal"] == 1687


async def test_runs_once_per_checkin_and_once_a_week(client):
    h = await onboard(client)
    await checkin(client, h, 14, 64.5)
    await checkin(client, h, 7, 64.5)  # adjusts: -100
    again = await checkin(client, h, 7, 64.4)  # editing the same check-in
    assert again["adjustment"] is None and "already adjusted" in again["adjustment_note"]
    soon = await checkin(client, h, 4, 64.4)  # 3 days later
    assert soon["adjustment"] is None and "once a week" in soon["adjustment_note"]
    assert (await target(client, h))["calories_kcal"] == 1587
    later = await checkin(client, h, 0, 64.4)  # a week after the last adjustment
    assert later["adjustment"] is not None


async def test_needs_a_check_in_from_about_a_week_ago(client):
    h = await onboard(client)
    await checkin(client, h, 2, 64.5)
    r = await checkin(client, h, 0, 64.0)
    assert r["adjustment"] is None and "about a week" in r["adjustment_note"]


async def test_backfilled_checkin_does_not_adjust(client):
    h = await onboard(client)
    await checkin(client, h, 0, 64.5)
    r = await checkin(client, h, 10, 66.0)
    assert r["adjustment"] is None and "newest" in r["adjustment_note"]


async def test_calorie_floor(client):
    h = await onboard(client, age=80, height_cm=140, weight_kg=38, days_per_week=2)
    await checkin(client, h, 7, 38.0)
    r = await checkin(client, h, 0, 38.0)
    assert r["adjustment"]["nutrition"]["after_kcal"] == 1200
    assert r["adjustment"]["nutrition"]["floor_applied"] is True


async def _latest_template(session) -> list[dict]:
    row = await session.scalar(
        select(TrainingPlan).order_by(TrainingPlan.created_at.desc(), TrainingPlan.id.desc())
    )
    return row.plan_json["template"]


async def _log_all_planned(client, h, start: int, end: int, *, beat_targets: bool):
    """Log every planned day from `start` to `end` days ago."""
    logged = 0
    for n in range(start, end - 1, -1):
        w = (await client.get("/api/v1/training/week", params={"day": day(n)}, headers=h)).json()
        d = next(x for x in w["days"] if x["day"] == day(n))
        if not d["session"]:
            continue
        sets = []
        if beat_targets:
            for p in d["session"]["exercises"]:
                key = "actual_reps" if p["type"] == "reps" else "actual_seconds"
                val = (p["target_reps"] or p["target_seconds"]) + 1
                sets += [
                    {"exercise_code": p["code"], "set_no": i, key: val}
                    for i in range(1, p["sets"] + 1)
                ]
        r = await client.put(
            f"/api/v1/training/workouts/{day(n)}", json={"status": "done", "sets": sets}, headers=h
        )
        assert r.status_code == 200, r.text
        logged += 1
    return logged


async def test_full_week_at_target_progresses_training(client, session):
    h = await onboard(client)
    await checkin(client, h, 7, 64.5)
    before = await _latest_template(session)
    assert await _log_all_planned(client, h, 7, 1, beat_targets=True) >= 2
    r = await checkin(client, h, 0, 64.3)
    t = r["adjustment"]["training"]
    assert t["decision"] == "progress"
    assert t["completion_pct"] == 100
    assert t["changes"]
    after = await _latest_template(session)
    b = before[0]["exercises"][0]
    a = after[0]["exercises"][0]
    if b["target_reps"] is not None:
        assert a["target_reps"] == min(b["reps_max"], b["target_reps"] + 2)
    w = (await client.get("/api/v1/training/week", headers=h)).json()
    assert w["note"] and "Updated after your check-in" in w["note"]


async def test_missed_week_removes_a_set(client, session):
    h = await onboard(client)
    await checkin(client, h, 7, 64.5)
    # Make sure last week's plans exist, but log nothing.
    for n in (7, 1):
        await client.get("/api/v1/training/week", params={"day": day(n)}, headers=h)
    before = await _latest_template(session)
    r = await checkin(client, h, 0, 64.5)
    assert r["adjustment"]["training"]["decision"] == "reduce"
    after = await _latest_template(session)
    for bs, as_ in zip(before, after, strict=True):
        for bp, ap in zip(bs["exercises"], as_["exercises"], strict=True):
            assert ap["sets"] == max(1, bp["sets"] - 1)


async def test_next_week_carries_progress(client, session):
    from app.models import Profile, User
    from app.services import training_service

    h = await onboard(client)
    await checkin(client, h, 7, 64.5)
    for n in (7, 1):
        await client.get("/api/v1/training/week", params={"day": day(n)}, headers=h)
    await checkin(client, h, 0, 64.5)  # reduce
    template = await _latest_template(session)

    user = await session.scalar(select(User))
    profile = await session.scalar(select(Profile))
    t = local_today(TZ)
    next_monday = t - timedelta(days=t.weekday()) + timedelta(days=7)
    plan = await training_service.ensure_plan(session, user, profile, next_monday)
    await session.commit()
    assert plan.week_start == next_monday
    assert plan.plan_json["sessions"] == template


async def test_isolation_between_users(client, make_client):
    ha = await onboard(client, "a@example.com")
    other = make_client()
    hb = await onboard(other, "b@example.com")
    await checkin(client, ha, 7, 64.5)
    await checkin(client, ha, 0, 64.4)
    assert (await other.get("/api/v1/checkins/adjustments", headers=hb)).json() == []
    assert (await target(other, hb))["calories_kcal"] == 1687
    r = await checkin(other, hb, 0, 60.0)
    assert r["adjustment"] is None and "starting point" in r["adjustment_note"]
