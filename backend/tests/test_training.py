from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from app.core.timeutil import local_today
from app.models import TrainingPlan
from tests.helpers import PROFILE, bearer, onboard, register

pytestmark = pytest.mark.anyio

TZ = PROFILE["timezone"]  # profile: lose_fat, beginner, 30 min, 3 days, no bar


def today() -> date:
    return local_today(TZ)


def monday() -> date:
    t = today()
    return t - timedelta(days=t.weekday())


async def week(client, h, day=None) -> dict:
    params = {"day": str(day)} if day else {}
    r = await client.get("/api/v1/training/week", params=params, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def planned_days(w: dict) -> list[dict]:
    return [d for d in w["days"] if d["session"]]


async def test_exercise_library(client):
    h = bearer(await register(client))
    items = (await client.get("/api/v1/exercises", headers=h)).json()
    assert len(items) >= 40
    one = (await client.get("/api/v1/exercises/pushup", headers=h)).json()
    assert one["group"] == "push" and one["harder"] and one["instructions"]
    assert (await client.get("/api/v1/exercises/nope", headers=h)).status_code == 404
    assert (await client.get("/api/v1/exercises")).status_code == 401


async def test_onboarding_creates_first_plan(client, session):
    h = await onboard(client)
    assert await session.scalar(select(func.count()).select_from(TrainingPlan)) == 1
    w = await week(client, h)
    assert w["week_start"] == str(monday())
    assert w["split"] == "Full body"
    assert len(w["days"]) == 7
    days = planned_days(w)
    assert [date.fromisoformat(d["day"]).weekday() for d in days] == [0, 2, 4]
    s = days[0]["session"]
    assert len(s["exercises"]) == 5  # 30 minutes
    assert s["finisher"]["group"] == "cardio"  # fat loss
    assert len(s["warmup"]) == 3 and len(s["cooldown"]) == 3
    assert all(e["sets"] == 2 for e in s["exercises"])  # beginner, fat loss 3 - 1
    assert {d["status"] for d in w["days"] if not d["session"]} == {"rest"}


async def test_statuses_and_future_week(client):
    h = await onboard(client)
    w = await week(client, h)
    for d in planned_days(w):
        expected = "planned" if d["day"] >= str(today()) else "not_logged"
        assert d["status"] == expected
    r = await client.get(
        "/api/v1/training/week", params={"day": str(monday() + timedelta(days=7))}, headers=h
    )
    assert r.status_code == 400 and r.json()["code"] == "future_week"
    last = await week(client, h, monday() - timedelta(days=7))
    assert last["week_start"] == str(monday() - timedelta(days=7))


async def _first_past_or_today_session(client, h) -> dict:
    """A planned day not after today, looking back up to two weeks."""
    for back in (0, 7, 14):
        w = await week(client, h, today() - timedelta(days=back))
        days = [d for d in planned_days(w) if d["day"] <= str(today())]
        if days:
            return days[-1]
    raise AssertionError("no planned day found")


async def test_log_workout_with_targets_from_plan(client):
    h = await onboard(client)
    d = await _first_past_or_today_session(client, h)
    s = d["session"]
    first, second = s["exercises"][0], s["exercises"][1]
    key = "actual_reps" if first["type"] == "reps" else "actual_seconds"
    target = first["target_reps"] or first["target_seconds"]
    sets = [
        {"exercise_code": first["code"], "set_no": 1, key: target + 2},
        {"exercise_code": first["code"], "set_no": 2, key: target - 1},
    ]
    r = await client.put(
        f"/api/v1/training/workouts/{d['day']}", json={"status": "done", "sets": sets}, headers=h
    )
    assert r.status_code == 200, r.text
    body = r.json()
    planned_sets = sum(e["sets"] for e in s["exercises"]) + s["finisher"]["sets"]
    summary = body["summary"]
    assert summary["sets_planned"] == planned_sets
    assert summary["sets_done"] == 2
    assert summary["targets_met"] == 1
    assert summary["exercises_skipped"] == len(s["exercises"])  # all but the first + finisher
    stored = [x for x in body["sets"] if x["exercise_code"] == second["code"]]
    assert all(x["actual_reps"] is None and x["actual_seconds"] is None for x in stored)

    w = await week(client, h, date.fromisoformat(d["day"]))
    assert next(x for x in w["days"] if x["day"] == d["day"])["status"] == "done"

    # Saving again replaces the log.
    r = await client.put(
        f"/api/v1/training/workouts/{d['day']}", json={"status": "skipped"}, headers=h
    )
    assert r.json()["status"] == "skipped" and r.json()["sets"] == []
    assert (
        await client.delete(f"/api/v1/training/workouts/{d['day']}", headers=h)
    ).status_code == 204
    r = await client.get(f"/api/v1/training/workouts/{d['day']}", headers=h)
    assert r.status_code == 404


async def test_workout_rules(client):
    h = await onboard(client)
    d = await _first_past_or_today_session(client, h)
    url = f"/api/v1/training/workouts/{d['day']}"
    ex = d["session"]["exercises"][0]
    bad = [
        ({"exercise_code": "pull_up", "set_no": 1, "actual_reps": 5}, "not_in_plan"),
        ({"exercise_code": ex["code"], "set_no": ex["sets"] + 1, "actual_reps": 5}, "bad_set"),
    ]
    for s, code in bad:
        r = await client.put(url, json={"status": "done", "sets": [s]}, headers=h)
        assert r.status_code == 400 and r.json()["code"] == code
    dup = {"exercise_code": ex["code"], "set_no": 1, "actual_reps": 5}
    r = await client.put(url, json={"status": "done", "sets": [dup, dup]}, headers=h)
    assert r.json()["code"] == "duplicate_set"

    w = await week(client, h)
    rest = next((x for x in w["days"] if not x["session"] and x["day"] <= str(today())), None)
    if rest:
        r = await client.put(
            f"/api/v1/training/workouts/{rest['day']}", json={"status": "done"}, headers=h
        )
        assert r.json()["code"] == "rest_day"
    future = str(today() + timedelta(days=1))
    r = await client.put(f"/api/v1/training/workouts/{future}", json={"status": "done"}, headers=h)
    assert r.status_code == 400 and r.json()["code"] in {"future_day", "future_week"}


async def test_workout_unlocks_milestone(client):
    h = await onboard(client)
    d = await _first_past_or_today_session(client, h)
    await client.put(f"/api/v1/training/workouts/{d['day']}", json={"status": "done"}, headers=h)
    ms = {m["code"]: m for m in (await client.get("/api/v1/milestones", headers=h)).json()}
    assert ms["workout_first"]["unlocked_at"] is not None
    await client.put(f"/api/v1/training/workouts/{d['day']}", json={"status": "skipped"}, headers=h)
    ms = {m["code"]: m for m in (await client.get("/api/v1/milestones", headers=h)).json()}
    assert ms["workout_first"]["unlocked_at"] is not None  # never cleared
    assert ms["workout_10"]["current"] == 0  # a skipped day is not a workout


async def test_profile_change_rebuilds_from_tomorrow(client, session):
    h = await onboard(client)
    before = await week(client, h)
    r = await client.put("/api/v1/profile", json=PROFILE | {"days_per_week": 6}, headers=h)
    assert r.status_code == 200
    assert await session.scalar(select(func.count()).select_from(TrainingPlan)) == 2
    after = await week(client, h)
    t = str(today())
    for b, a in zip(before["days"], after["days"], strict=True):
        if a["day"] <= t:
            assert (b["session"] is None) == (a["session"] is None)  # past and today kept
    future = [d for d in after["days"] if d["day"] > t]
    # From tomorrow, 6-day plan: every day except Sunday has a session.
    assert all(
        (d["session"] is not None) == (date.fromisoformat(d["day"]).weekday() < 6) for d in future
    )

    # A change that does not affect training keeps the plan.
    await client.put("/api/v1/profile", json=PROFILE | {"days_per_week": 6, "name": "X"}, headers=h)
    assert await session.scalar(select(func.count()).select_from(TrainingPlan)) == 2


async def test_today_shows_workout(client):
    h = await onboard(client, days_per_week=6)
    t = (await client.get("/api/v1/today", headers=h)).json()
    if today().weekday() == 6:
        assert t["workout"] is None
    else:
        assert t["workout"]["status"] == "planned"
        assert t["workout"]["exercise_count"] == 5


async def test_isolation_between_users(client, make_client):
    ha = await onboard(client, "a@example.com")
    other = make_client()
    hb = await onboard(other, "b@example.com", days_per_week=2, goal="build_muscle")
    d = await _first_past_or_today_session(client, ha)
    await client.put(f"/api/v1/training/workouts/{d['day']}", json={"status": "done"}, headers=ha)

    # B sees their own plan and never A's log.
    wb = await week(other, hb, date.fromisoformat(d["day"]))
    assert len(planned_days(wb)) == 2
    assert all(x["status"] != "done" for x in wb["days"])
    assert (await other.get(f"/api/v1/training/workouts/{d['day']}", headers=hb)).status_code == 404
    assert (
        await other.delete(f"/api/v1/training/workouts/{d['day']}", headers=hb)
    ).status_code == 404
    assert (
        await client.get(f"/api/v1/training/workouts/{d['day']}", headers=ha)
    ).status_code == 200
