from datetime import timedelta

import pytest

from app.core.timeutil import local_today
from tests.helpers import PROFILE, onboard

pytestmark = pytest.mark.anyio

URL = "/api/v1/checkins"


def today():
    return local_today(PROFILE["timezone"])


def day(n: int) -> str:
    return str(today() - timedelta(days=n))


async def profile_weight(client, h) -> float:
    return (await client.get("/api/v1/profile", headers=h)).json()["weight_kg"]


async def test_status_and_due_rule(client):
    h = await onboard(client)
    s = (await client.get(f"{URL}/status", headers=h)).json()
    assert s["due"] is True and s["last_day"] is None
    await client.put(f"{URL}/{day(7)}", json={"weight_kg": 70}, headers=h)
    s = (await client.get(f"{URL}/status", headers=h)).json()
    assert (s["due"], s["days_since"]) == (False, 7)
    assert (await client.get("/api/v1/today", headers=h)).json()["checkin_due"] is False
    await client.delete(f"{URL}/{day(7)}", headers=h)
    await client.put(f"{URL}/{day(8)}", json={"weight_kg": 70}, headers=h)
    assert (await client.get(f"{URL}/status", headers=h)).json()["due"] is True
    assert (await client.get("/api/v1/today", headers=h)).json()["checkin_due"] is True


async def test_save_list_changes_and_profile_weight(client):
    h = await onboard(client)  # profile weight 64.5
    r = await client.put(
        f"{URL}/{day(14)}", json={"weight_kg": 66.0, "waist_cm": 80, "note": " start "}, headers=h
    )
    assert r.status_code == 200
    assert r.json()["weight_change_kg"] is None and r.json()["note"] == "start"
    assert await profile_weight(client, h) == 66.0

    r = await client.put(f"{URL}/{day(7)}", json={"weight_kg": 65.2, "waist_cm": 79}, headers=h)
    assert r.json()["weight_change_kg"] == -0.8
    assert r.json()["waist_change_cm"] == -1.0
    assert await profile_weight(client, h) == 65.2

    # Back-filling an older check-in does not change the current weight.
    await client.put(f"{URL}/{day(21)}", json={"weight_kg": 67.0}, headers=h)
    assert await profile_weight(client, h) == 65.2

    rows = (await client.get(URL, headers=h)).json()
    assert [r["day"] for r in rows] == [day(7), day(14), day(21)]
    assert [r["weight_change_kg"] for r in rows] == [-0.8, -1.0, None]


async def test_rules(client):
    h = await onboard(client)
    future = str(today() + timedelta(days=1))
    r = await client.put(f"{URL}/{future}", json={"weight_kg": 70}, headers=h)
    assert r.status_code == 400
    for body in ({}, {"weight_kg": 20}, {"weight_kg": 70, "waist_cm": 10}):
        assert (await client.put(f"{URL}/{day(0)}", json=body, headers=h)).status_code == 422
    assert (await client.delete(f"{URL}/{day(3)}", headers=h)).status_code == 404


async def test_isolation_between_users(client, make_client):
    ha = await onboard(client, "a@example.com")
    other = make_client()
    hb = await onboard(other, "b@example.com")
    await client.put(f"{URL}/{day(0)}", json={"weight_kg": 80}, headers=ha)
    assert (await other.get(URL, headers=hb)).json() == []
    assert (await other.get(f"{URL}/status", headers=hb)).json()["due"] is True
    assert (await other.delete(f"{URL}/{day(0)}", headers=hb)).status_code == 404
    assert (await client.get(URL, headers=ha)).json()[0]["weight_kg"] == 80
    assert await profile_weight(other, hb) == PROFILE["weight_kg"]
