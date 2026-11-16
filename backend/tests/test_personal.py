"""M14: plate tips, mess plate, easy day, calendar events and the quiet-days nudge."""

from datetime import timedelta

import pytest
from sqlalchemy import update

from app.core.timeutil import local_today
from app.models import User
from tests.helpers import PROFILE, onboard

pytestmark = pytest.mark.anyio


def today():
    return local_today(PROFILE["timezone"])


async def test_plate_tips_for_usual_foods(client):
    h = await onboard(client, usual_foods=["steamed_rice", "dal_tadka", "samosa"])
    t = (await client.get("/api/v1/nutrition/plate-tips", headers=h)).json()
    assert t["goal"] == "lose_fat"
    by = {x["food_code"]: x for x in t["tips"]}
    assert list(by) == ["steamed_rice", "dal_tadka", "samosa"]
    assert by["steamed_rice"]["servings"] == 0.75 and by["steamed_rice"]["grams"] == 120
    assert all(x["tip"].startswith("Keep") for x in t["tips"])
    h2 = await onboard(client, "b@example.com")
    assert (await client.get("/api/v1/nutrition/plate-tips", headers=h2)).json()["tips"] == []


async def test_mess_plate(client):
    h = await onboard(client)  # veg
    body = {"meal_type": "lunch", "food_codes": ["dal_tadka", "steamed_rice", "chicken_curry"]}
    r = await client.post(f"/api/v1/nutrition/days/{today()}/mess-plate", json=body, headers=h)
    assert r.status_code == 200, r.text
    p = r.json()
    codes = [i["food_code"] for i in p["items"]]
    assert "chicken_curry" not in codes  # outside the diet: left out
    assert codes[0] == "dal_tadka"
    assert p["calories_kcal"] <= p["budget_kcal"]
    # Nothing was logged.
    day = (await client.get(f"/api/v1/nutrition/days/{today()}", headers=h)).json()
    assert day["eaten"]["calories_kcal"] == 0
    bad = body | {"food_codes": ["nope"]}
    r = await client.post(f"/api/v1/nutrition/days/{today()}/mess-plate", json=bad, headers=h)
    assert r.status_code == 404
    future = today() + timedelta(days=1)
    r = await client.post(f"/api/v1/nutrition/days/{future}/mess-plate", json=body, headers=h)
    assert r.status_code == 400


async def test_easy_day_counts_for_streak_with_weekly_limit(client, session):
    h = await onboard(client)
    e = (await client.get("/api/v1/activity/easy-day", headers=h)).json()
    assert e["taken"] is False and e["minutes"] == 10 and len(e["plan"]) == 6
    assert e["left_this_week"] == 2 and e["per_week"] == 2
    before = (await client.get("/api/v1/today", headers=h)).json()
    assert before["current_streak"] == 0 and before["easy_day"] is False

    r = await client.post("/api/v1/activity/easy-day", headers=h)
    assert r.status_code == 200 and r.json()["taken"] is True
    again = await client.post("/api/v1/activity/easy-day", headers=h)  # repeat is fine
    assert again.json()["left_this_week"] == r.json()["left_this_week"]
    t = (await client.get("/api/v1/today", headers=h)).json()
    assert t["easy_day"] is True and t["current_streak"] == 1
    summary = (await client.get("/api/v1/activity/summary?days=7", headers=h)).json()
    assert summary["current_streak"] == 1

    r = await client.delete("/api/v1/activity/easy-day", headers=h)
    assert r.json()["taken"] is False
    assert (await client.get("/api/v1/today", headers=h)).json()["current_streak"] == 0


async def test_easy_day_limit(client, session, monkeypatch):
    from datetime import date

    from app.models import EasyDay
    from app.services import activity_service

    wednesday = date(2026, 11, 11)
    monkeypatch.setattr(activity_service, "local_today", lambda tz: wednesday)
    h = await onboard(client)
    uid = (await client.get("/api/v1/auth/me", headers=h)).json()["id"]
    session.add(EasyDay(user_id=uid, day=date(2026, 11, 9)))
    await session.commit()
    r = await client.post("/api/v1/activity/easy-day", headers=h)
    assert r.status_code == 200 and r.json()["left_this_week"] == 0
    monkeypatch.setattr(activity_service, "local_today", lambda tz: date(2026, 11, 12))
    r = await client.post("/api/v1/activity/easy-day", headers=h)
    assert r.status_code == 409 and r.json()["code"] == "easy_days_used"
    # A new week starts on Monday.
    monkeypatch.setattr(activity_service, "local_today", lambda tz: date(2026, 11, 16))
    r = await client.post("/api/v1/activity/easy-day", headers=h)
    assert r.status_code == 200 and r.json()["left_this_week"] == 1


async def test_quiet_user_is_offered_an_easy_day(client, session):
    from app.services.bounce.llm import get_llm

    h = await onboard(client)
    client._transport.app.dependency_overrides[get_llm] = lambda: None
    n = (await client.get("/api/v1/bounce/status", headers=h)).json()["notification"]
    assert n["kind"] != "easy"  # a new account is not "quiet"
    await session.execute(update(User).values(created_at=User.created_at - timedelta(days=10)))
    await session.commit()
    e = (await client.get("/api/v1/activity/easy-day", headers=h)).json()
    assert e["suggested"] is True
    n = (await client.get("/api/v1/bounce/status", headers=h)).json()["notification"]
    assert n["kind"] == "easy" and n["action_label"] == "Easy day"
    await client.post("/api/v1/activity/easy-day", headers=h)
    n = (await client.get("/api/v1/bounce/status", headers=h)).json()["notification"]
    assert n is None or n["kind"] != "easy"


async def test_today_lists_calendar_events(client, monkeypatch):
    from app.engines.calendar_engine import Event
    from app.services import calendar_service

    on = Event("test_fest", "Test festival", "festival", True, "01-01", "12-31", (), "Enjoy.")
    south = Event("south_only", "South", "season", True, "01-01", "12-31", ("south",), "Rain.")
    monkeypatch.setattr(calendar_service, "calendar_events", lambda: (on, south))
    h = await onboard(client)  # no state: no region
    events = (await client.get("/api/v1/today", headers=h)).json()["events"]
    assert events == [
        {"code": "test_fest", "name": "Test festival", "kind": "festival", "tip": "Enjoy."}
    ]
    h2 = await onboard(client, "b@example.com", state="KL")
    codes = [e["code"] for e in (await client.get("/api/v1/today", headers=h2)).json()["events"]]
    assert codes == ["test_fest", "south_only"]


async def test_easy_day_is_per_user(client):
    a = await onboard(client)
    await client.post("/api/v1/activity/easy-day", headers=a)
    b = await onboard(client, "b@example.com")
    assert (await client.get("/api/v1/activity/easy-day", headers=b)).json()["taken"] is False
    assert (await client.get("/api/v1/today", headers=b)).json()["current_streak"] == 0
