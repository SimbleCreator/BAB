from datetime import timedelta

import pytest

from app.core.timeutil import local_today
from tests.helpers import PROFILE, onboard

pytestmark = pytest.mark.anyio

URL = "/api/v1/milestones"


def day(n: int) -> str:
    return str(local_today(PROFILE["timezone"]) - timedelta(days=n))


async def unlocked(client, h) -> set[str]:
    return {m["code"] for m in (await client.get(URL, headers=h)).json() if m["unlocked_at"]}


async def test_list_shows_all_with_progress(client):
    h = await onboard(client)
    await client.put(f"/api/v1/activity/{day(0)}", json={"steps": 3000}, headers=h)
    items = {m["code"]: m for m in (await client.get(URL, headers=h)).json()}
    assert len(items) == 17
    assert items["steps_5k_day"]["current"] == 3000
    assert items["steps_5k_day"]["unlocked_at"] is None
    assert items["run_5k"]["unit"] == "m"


async def test_unlocks_from_activity_runs_and_checkins(client):
    h = await onboard(client, daily_step_goal=5000)
    for i in range(7):
        await client.put(f"/api/v1/activity/{day(i)}", json={"steps": 10_500}, headers=h)
    await client.post(
        "/api/v1/runs", json={"day": day(1), "distance_m": 10_000, "duration_s": 3600}, headers=h
    )
    for i in range(4):
        await client.put(f"/api/v1/checkins/{day(i * 7)}", json={"weight_kg": 64}, headers=h)
    assert await unlocked(client, h) == {
        "steps_5k_day",
        "steps_10k_day",
        "streak_7",
        "run_first",
        "run_5k",
        "run_10k",
        "checkins_4",
    }


async def test_csv_import_unlocks(client):
    h = await onboard(client)
    content = f"date,steps,distance_km,active_kcal\n{day(1)},12000,,\n".encode()
    await client.post(
        "/api/v1/activity/import", files={"file": ("a.csv", content, "text/csv")}, headers=h
    )
    assert "steps_10k_day" in await unlocked(client, h)


async def test_unlocks_are_never_cleared(client):
    h = await onboard(client)
    r = await client.post(
        "/api/v1/runs", json={"day": day(0), "distance_m": 5000, "duration_s": 1500}, headers=h
    )
    await client.delete(f"/api/v1/runs/{r.json()['id']}", headers=h)
    assert {"run_first", "run_5k"} <= await unlocked(client, h)


async def test_seen_flow_and_today_banner(client):
    h = await onboard(client)
    await client.put(f"/api/v1/activity/{day(0)}", json={"steps": 6000}, headers=h)
    today = (await client.get("/api/v1/today", headers=h)).json()
    assert today["new_milestones"] == [{"code": "steps_5k_day", "title": "5K step day"}]
    items = {m["code"]: m for m in (await client.get(URL, headers=h)).json()}
    assert items["steps_5k_day"]["seen"] is False
    assert (await client.post(f"{URL}/seen", headers=h)).status_code == 204
    assert (await client.get("/api/v1/today", headers=h)).json()["new_milestones"] == []
    items = {m["code"]: m for m in (await client.get(URL, headers=h)).json()}
    assert items["steps_5k_day"]["seen"] is True


async def test_isolation_between_users(client, make_client):
    ha = await onboard(client, "a@example.com")
    other = make_client()
    hb = await onboard(other, "b@example.com")
    await client.put(f"/api/v1/activity/{day(0)}", json={"steps": 20_000}, headers=ha)
    assert await unlocked(other, hb) == set()
    items = {m["code"]: m for m in (await other.get(URL, headers=hb)).json()}
    assert items["steps_5k_day"]["current"] == 0
    await other.post(f"{URL}/seen", headers=hb)
    today = (await client.get("/api/v1/today", headers=ha)).json()
    assert len(today["new_milestones"]) == 2  # B marking seen does not touch A


async def test_catch_up_for_data_saved_before_evaluation(client, session):
    from sqlalchemy import text

    h = await onboard(client)
    await client.put(f"/api/v1/activity/{day(0)}", json={"steps": 6000}, headers=h)
    await session.execute(text("DELETE FROM milestones"))  # as if it never ran
    await session.commit()
    today = (await client.get("/api/v1/today", headers=h)).json()
    assert [m["code"] for m in today["new_milestones"]] == ["steps_5k_day"]
