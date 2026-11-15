from datetime import timedelta

import pytest
from sqlalchemy import text

from app.core.timeutil import local_today
from tests.helpers import PROFILE, bearer, onboard, register

pytestmark = pytest.mark.anyio

URL = "/api/v1/habits"
TZ = PROFILE["timezone"]


def today():
    return local_today(TZ)


async def start(client, h, kind="smoking", baseline=20, pace=10) -> dict:
    r = await client.post(
        URL, json={"type": kind, "baseline": baseline, "pace_pct": pace}, headers=h
    )
    assert r.status_code == 201, r.text
    return r.json()


async def test_start_smoking_plan(client):
    h = await onboard(client)
    s = await start(client, h)
    assert s["habit"]["period"] == "day"
    assert s["habit"]["started_on"] == str(today())
    assert s["week_number"] == 1
    assert s["allowance_per_period"] == 18  # 20 x (1 - 0.10 x 1)
    assert s["week_allowance"] == 126
    a = s["availability"]
    assert a["period"] == "day" and a["allowance"] == 18
    assert a["unlocked"] == 18 * s["goals_today"]["met"] // 3
    assert a["locked"] == 18 - a["unlocked"]
    assert "doctor" in s["doctor_line"].lower()


async def test_one_plan_per_type_and_validation(client):
    h = await onboard(client)
    await start(client, h)
    r = await client.post(URL, json={"type": "smoking", "baseline": 5, "pace_pct": 5}, headers=h)
    assert r.status_code == 409
    await start(client, h, "drinking", 10, 5)
    assert len((await client.get(URL, headers=h)).json()) == 2
    for body in (
        {"type": "vaping", "baseline": 5, "pace_pct": 5},
        {"type": "smoking", "baseline": 0, "pace_pct": 5},
        {"type": "smoking", "baseline": 5, "pace_pct": 7},
    ):
        assert (await client.post(URL, json=body, headers=h)).status_code == 422


async def test_requires_profile(client):
    h = bearer(await register(client))
    r = await client.post(URL, json={"type": "smoking", "baseline": 5, "pace_pct": 5}, headers=h)
    assert r.status_code == 409


async def test_goals_unlock_thirds(client):
    h = await onboard(client, daily_step_goal=5000)
    s = await start(client, h, baseline=9, pace=10)  # 8.1 -> 8 per day
    met_before = s["goals_today"]["met"]
    await client.put(f"/api/v1/activity/{today()}", json={"steps": 6000}, headers=h)
    for meal in ("breakfast", "lunch"):
        await client.post(
            f"/api/v1/nutrition/days/{today()}/items",
            json={"meal_type": meal, "food_code": "idli", "servings": 1},
            headers=h,
        )
    s = (await client.get(URL, headers=h)).json()[0]
    g = s["goals_today"]
    assert g["steps"] and g["meals"]
    assert g["met"] >= max(2, met_before)
    assert s["availability"]["unlocked"] == 8 * g["met"] // 3


async def test_one_tap_and_edit_days(client):
    h = await onboard(client)
    s = await start(client, h)
    hid = s["habit"]["id"]
    for _ in range(3):
        s = (await client.post(f"{URL}/{hid}/log", headers=h)).json()
    assert s["today_used"] == 3 and s["availability"]["used"] == 3
    r = await client.put(f"{URL}/{hid}/days/{today()}", json={"units": 1}, headers=h)
    assert r.json()["today_used"] == 1
    future = today() + timedelta(days=1)
    assert (
        await client.put(f"{URL}/{hid}/days/{future}", json={"units": 1}, headers=h)
    ).status_code == 400
    before = today() - timedelta(days=1)
    r = await client.put(f"{URL}/{hid}/days/{before}", json={"units": 1}, headers=h)
    assert r.status_code == 400 and r.json()["code"] == "before_start"
    days = (
        await client.get(
            f"{URL}/{hid}/days", params={"from": str(today()), "to": str(today())}, headers=h
        )
    ).json()
    assert days == [{"day": str(today()), "units": 1}]


async def _backdate(session, days: int):
    await session.execute(
        text("UPDATE habits SET started_on = started_on - CAST(:d AS integer)"), {"d": days}
    )
    await session.commit()


async def test_week_within_moves_on_and_over_repeats(client, session):
    h = await onboard(client)
    s = await start(client, h, baseline=10, pace=10)  # week 1: 9/day = 63/week
    hid = s["habit"]["id"]
    await _backdate(session, 21)
    started = today() - timedelta(days=21)
    # Week 1: 8 a day (56, within). Week 2 at step 2 (8/day = 56): 9 a day (63, over).
    for i in range(7):
        await client.put(
            f"{URL}/{hid}/days/{started + timedelta(days=i)}", json={"units": 8}, headers=h
        )
    for i in range(7, 14):
        await client.put(
            f"{URL}/{hid}/days/{started + timedelta(days=i)}", json={"units": 9}, headers=h
        )
    weeks = (await client.get(f"{URL}/{hid}/weeks", headers=h)).json()
    assert [w["number"] for w in weeks] == [3, 2, 1]
    w1 = weeks[-1]
    assert (w1["step"], w1["allowance_total"], w1["used"], w1["within"], w1["avoided"]) == (
        1,
        63,
        56,
        True,
        14,
    )
    w2 = weeks[-2]
    assert (w2["step"], w2["allowance_total"], w2["within"], w2["avoided"]) == (2, 56, False, 0)
    w3 = weeks[0]  # nothing logged: within, repeats step 2 because week 2 was over
    assert (w3["step"], w3["within"], w3["avoided"]) == (2, True, 70)
    s = (await client.get(URL, headers=h)).json()[0]
    assert s["week_number"] == 4
    assert s["allowance_per_period"] == 7  # step 3
    assert s["last_week"]["number"] == 3
    ms = {m["code"]: m for m in (await client.get("/api/v1/milestones", headers=h)).json()}
    assert ms["habit_week_within"]["unlocked_at"] is not None


async def test_drinking_is_weekly(client):
    h = await onboard(client)
    s = await start(client, h, "drinking", 14, 10)  # 12.6 -> 13 per week
    assert s["habit"]["period"] == "week"
    assert s["allowance_per_period"] == 13 and s["week_allowance"] == 13
    assert s["availability"]["period"] == "week"
    assert s["availability"]["unlocked"] <= 13


async def test_stop_and_delete(client):
    h = await onboard(client)
    hid = (await start(client, h))["habit"]["id"]
    r = await client.post(f"{URL}/{hid}/stop", headers=h)
    assert r.json()["active"] is False
    assert (await client.get(URL, headers=h)).json() == []
    r = await client.post(f"{URL}/{hid}/log", headers=h)
    assert r.status_code == 409
    await start(client, h)  # a new plan of the same type can start
    assert (await client.delete(f"{URL}/{hid}", headers=h)).status_code == 204
    assert (await client.get(f"{URL}/{hid}/weeks", headers=h)).status_code == 404


async def test_today_shows_plans(client):
    h = await onboard(client)
    assert (await client.get("/api/v1/today", headers=h)).json()["habits"] == []
    await start(client, h)
    t = (await client.get("/api/v1/today", headers=h)).json()["habits"]
    assert t[0]["type"] == "smoking" and t[0]["availability"]["allowance"] == 18


async def test_isolation_between_users(client, make_client):
    ha = await onboard(client, "a@example.com")
    other = make_client()
    hb = await onboard(other, "b@example.com")
    hid = (await start(client, ha))["habit"]["id"]
    await client.post(f"{URL}/{hid}/log", headers=ha)
    assert (await other.get(URL, headers=hb)).json() == []
    assert (await other.post(f"{URL}/{hid}/log", headers=hb)).status_code == 404
    assert (
        await other.put(f"{URL}/{hid}/days/{today()}", json={"units": 50}, headers=hb)
    ).status_code == 404
    assert (await other.get(f"{URL}/{hid}/weeks", headers=hb)).status_code == 404
    assert (await other.post(f"{URL}/{hid}/stop", headers=hb)).status_code == 404
    assert (await other.delete(f"{URL}/{hid}", headers=hb)).status_code == 404
    # B can start their own smoking plan; A's is untouched.
    await start(other, hb)
    assert (await client.get(URL, headers=ha)).json()[0]["today_used"] == 1
