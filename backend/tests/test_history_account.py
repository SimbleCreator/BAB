import json
from datetime import timedelta

import pytest
from sqlalchemy import func, select, text

from app.core.timeutil import local_today
from app.models import Base
from tests.helpers import PASSWORD, PROFILE, onboard

pytestmark = pytest.mark.anyio

TZ = PROFILE["timezone"]


def day(n: int = 0):
    return local_today(TZ) - timedelta(days=n)


async def fill_day(client, h, d):
    await client.put(f"/api/v1/activity/{d}", json={"steps": 9000}, headers=h)
    await client.post(
        "/api/v1/runs", json={"day": str(d), "distance_m": 3000, "duration_s": 1100}, headers=h
    )
    await client.post(
        f"/api/v1/nutrition/days/{d}/items",
        json={"meal_type": "lunch", "food_code": "rajma", "servings": 1},
        headers=h,
    )
    await client.put(f"/api/v1/checkins/{d}", json={"weight_kg": 64}, headers=h)
    await client.post(
        "/api/v1/habits", json={"type": "smoking", "baseline": 5, "pace_pct": 5}, headers=h
    )
    habits = (await client.get("/api/v1/habits", headers=h)).json()
    await client.put(
        f"/api/v1/habits/{habits[0]['habit']['id']}/days/{local_today(TZ)}",
        json={"units": 2},
        headers=h,
    )


async def test_month_overview(client):
    h = await onboard(client)
    today = local_today(TZ)
    await fill_day(client, h, today)
    m = (await client.get("/api/v1/history/month", headers=h)).json()
    assert m["month"] == f"{today:%Y-%m}"
    assert len(m["days"]) >= 28
    t = next(x for x in m["days"] if x["day"] == str(today))
    assert (t["activity"], t["meals"], t["checkin"], t["runs"]) == (True, True, True, 1)
    empty = next(x for x in m["days"] if x["day"] != str(today))
    assert (empty["activity"], empty["meals"], empty["checkin"], empty["runs"]) == (
        False,
        False,
        False,
        0,
    )
    nxt = (today.replace(day=28) + timedelta(days=5)).strftime("%Y-%m")
    assert (
        await client.get("/api/v1/history/month", params={"month": nxt}, headers=h)
    ).status_code == 400
    bad = await client.get("/api/v1/history/month", params={"month": "2026-13"}, headers=h)
    assert bad.status_code == 400 and bad.json()["code"] == "bad_month"
    past = (
        await client.get("/api/v1/history/month", params={"month": "2025-02"}, headers=h)
    ).json()
    assert len(past["days"]) == 28


async def test_day_detail(client):
    h = await onboard(client)
    today = local_today(TZ)
    await fill_day(client, h, today)
    d = (await client.get(f"/api/v1/history/days/{today}", headers=h)).json()
    assert d["activity"]["steps"] == 9000
    assert len(d["runs"]) == 1 and d["runs"][0]["distance_m"] == 3000
    assert d["nutrition"]["eaten"]["calories_kcal"] == 220
    assert d["checkin"]["weight_kg"] == 64
    assert d["habits"][0]["units"] == 2
    future = today + timedelta(days=1)
    assert (await client.get(f"/api/v1/history/days/{future}", headers=h)).status_code == 400


async def test_workout_in_history(client):
    h = await onboard(client)
    for back in range(0, 7):
        d = day(back)
        w = (await client.get("/api/v1/training/week", params={"day": str(d)}, headers=h)).json()
        planned = next(x for x in w["days"] if x["day"] == str(d))
        if planned["session"]:
            await client.put(f"/api/v1/training/workouts/{d}", json={"status": "done"}, headers=h)
            m = (
                await client.get("/api/v1/history/month", params={"month": f"{d:%Y-%m}"}, headers=h)
            ).json()
            assert next(x for x in m["days"] if x["day"] == str(d))["workout"] == "done"
            detail = (await client.get(f"/api/v1/history/days/{d}", headers=h)).json()
            assert detail["workout"]["status"] == "done" and detail["workout_title"]
            return
    pytest.fail("no planned day in the last week")


async def test_export(client):
    h = await onboard(client)
    await fill_day(client, h, local_today(TZ))
    r = await client.get("/api/v1/account/export", headers=h)
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    data = r.json()
    assert data["account"]["email"] == "a@example.com"
    assert data["profile"]["name"] == PROFILE["name"]
    assert len(data["daily_activity"]) == 1 and len(data["runs"]) == 1
    assert data["meals"][0]["items"][0]["food_code"] == "rajma"
    assert data["habits"][0]["logs"][0]["units"] == 2
    assert data["nutrition_targets"] and data["training_plans"]
    raw = json.dumps(data)
    assert "password" not in raw and "token" not in raw


async def test_delete_account_removes_everything(client, make_client, session):
    h = await onboard(client, "a@example.com")
    other = make_client()
    hb = await onboard(other, "b@example.com")
    await fill_day(client, h, local_today(TZ))
    await fill_day(other, hb, local_today(TZ))

    r = await client.post(
        "/api/v1/account/delete", json={"password": "wrong-one-1", "confirm": True}, headers=h
    )
    assert r.status_code == 400
    r = await client.post(
        "/api/v1/account/delete", json={"password": PASSWORD, "confirm": False}, headers=h
    )
    assert r.status_code == 422
    r = await client.post(
        "/api/v1/account/delete", json={"password": PASSWORD, "confirm": True}, headers=h
    )
    assert r.status_code == 204
    assert (await client.get("/api/v1/auth/me", headers=h)).status_code == 401
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401
    login = await client.post(
        "/api/v1/auth/login", json={"email": "a@example.com", "password": PASSWORD}
    )
    assert login.status_code == 401

    # Every table holds rows for user B only.
    b_id = await session.scalar(text("SELECT id FROM users WHERE email = 'b@example.com'"))
    assert await session.scalar(select(func.count()).select_from(text("users"))) == 1
    for table in Base.metadata.sorted_tables:
        if "user_id" in table.c:
            n = await session.scalar(
                select(func.count()).select_from(table).where(table.c.user_id != b_id)
            )
            assert n == 0, table.name
    for child, parent in (
        ("run_points", "runs"),
        ("workout_sets", "workout_sessions"),
        ("meal_items", "meals"),
        ("habit_logs", "habits"),
    ):
        fk = {
            "runs": "run_id",
            "workout_sessions": "session_id",
            "meals": "meal_id",
            "habits": "habit_id",
        }[parent]
        c_t, p_t = Base.metadata.tables[child], Base.metadata.tables[parent]
        orphans = await session.scalar(
            select(func.count())
            .select_from(c_t.outerjoin(p_t, p_t.c.id == c_t.c[fk]))
            .where(p_t.c.id.is_(None))
        )
        assert orphans == 0, child
    assert (await other.get(f"/api/v1/history/days/{local_today(TZ)}", headers=hb)).json()[
        "activity"
    ]


async def test_public_config_no_auth(client):
    r = await client.get("/api/v1/config/public")
    assert r.status_code == 200
    assert r.json()["contact_email"] and r.json()["app_name"] == "B.A.B"


async def test_admin_stats(client, make_client, session):
    h = await onboard(client, "admin@example.com")
    other = make_client()
    await onboard(other, "user@example.com")
    assert (await client.get("/api/v1/admin/stats", headers=h)).status_code == 403
    await session.execute(
        text("UPDATE users SET is_admin = true WHERE email = 'admin@example.com'")
    )
    await session.commit()
    r = await client.get("/api/v1/admin/stats", headers=h)
    assert r.status_code == 200
    s = r.json()
    assert s["total_users"] == 2
    assert s["active_7_days"] == 2 and s["active_30_days"] == 2
    assert len(s["new_users_per_week"]) == 12
    assert s["new_users_per_week"][-1]["count"] == 2
    assert set(s["records"]) >= {"daily_activity", "runs", "meals", "checkins", "habits"}
    assert "@" not in r.text  # aggregates only


async def test_history_isolation(client, make_client):
    ha = await onboard(client, "a@example.com")
    other = make_client()
    hb = await onboard(other, "b@example.com")
    await fill_day(client, ha, local_today(TZ))
    m = (await other.get("/api/v1/history/month", headers=hb)).json()
    assert not any(d["activity"] or d["meals"] or d["checkin"] or d["runs"] for d in m["days"])
    d = (await other.get(f"/api/v1/history/days/{local_today(TZ)}", headers=hb)).json()
    assert d["activity"] is None and d["runs"] == [] and d["checkin"] is None and d["habits"] == []
    data = (await other.get("/api/v1/account/export", headers=hb)).json()
    assert data["daily_activity"] == [] and data["runs"] == [] and data["habits"] == []
