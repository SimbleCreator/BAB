from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select

from app.core.timeutil import local_today
from app.models import RunPoint
from tests.gpx_helpers import gpx_bytes, track
from tests.helpers import PROFILE, onboard

pytestmark = pytest.mark.anyio

URL = "/api/v1/runs"
TZ = PROFILE["timezone"]
WEIGHT = PROFILE["weight_kg"]


def today():
    return local_today(TZ)


def manual(day=None, **over):
    return {"day": str(day or today()), "distance_m": 5000, "duration_s": 1650} | over


def gpx_file(points):
    return {"file": ("run.gpx", gpx_bytes(points), "application/gpx+xml")}


def yesterday_morning_utc():
    local = datetime.combine(today() - timedelta(days=1), time(6, 30), ZoneInfo(TZ))
    return local.astimezone(timezone.utc)


async def test_manual_run(client):
    h = await onboard(client)
    r = await client.post(URL, json=manual(note=" park loop "), headers=h)
    assert r.status_code == 201
    run = r.json()
    assert run["source"] == "manual"
    assert run["pace_s_per_km"] == 330
    assert run["calories_kcal"] == round(WEIGHT * 5 * 1.036)
    assert run["calories_estimated"] is True
    assert run["has_track"] is False
    assert run["splits"] == [] and run["track"] == []
    assert run["note"] == "park loop"


async def test_manual_run_rules(client):
    h = await onboard(client)
    future = today() + timedelta(days=1)
    r = await client.post(URL, json=manual(day=future), headers=h)
    assert r.status_code == 400 and r.json()["code"] == "future_day"
    for over in ({"distance_m": 5}, {"duration_s": 10}, {"distance_m": 300_001}):
        assert (await client.post(URL, json=manual(**over), headers=h)).status_code == 422


async def test_list_newest_first(client):
    h = await onboard(client)
    for i in (3, 0, 7):
        await client.post(URL, json=manual(day=today() - timedelta(days=i)), headers=h)
    body = (await client.get(URL, headers=h)).json()
    assert body["total"] == 3
    days = [r["day"] for r in body["items"]]
    assert days == sorted(days, reverse=True)
    page = (await client.get(URL, params={"limit": 1, "offset": 1}, headers=h)).json()
    assert len(page["items"]) == 1 and page["items"][0]["day"] == days[1]


async def test_gpx_upload(client):
    h = await onboard(client)
    start = yesterday_morning_utc()
    r = await client.post(
        f"{URL}/gpx",
        files=gpx_file(track(26, 100, 30, start=start)),
        data={"note": "hills"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    run = r.json()
    assert run["source"] == "gpx"
    assert run["day"] == str(today() - timedelta(days=1))  # local date of the start
    assert run["distance_m"] == 2500
    assert run["duration_s"] == 750
    assert run["has_track"] is True
    assert len(run["track"]) == 26
    assert [s["distance_m"] for s in run["splits"]] == [1000, 1000, 500]
    assert run["note"] == "hills"
    listed = (await client.get(URL, headers=h)).json()["items"][0]
    assert listed["has_track"] is True


async def test_gpx_downsampled_to_2000_points(client, session):
    h = await onboard(client)
    pts = track(5000, 2, 1, start=yesterday_morning_utc())  # 10 km, 5000 points
    r = await client.post(f"{URL}/gpx", files=gpx_file(pts), headers=h)
    assert r.status_code == 201
    assert r.json()["distance_m"] == 9998  # measured on the full track
    count = await session.scalar(select(func.count()).select_from(RunPoint))
    assert count == 2000


async def test_gpx_errors(client):
    h = await onboard(client)
    bad = {"file": ("x.gpx", b"<gpx></gpx>", "application/gpx+xml")}
    r = await client.post(f"{URL}/gpx", files=bad, headers=h)
    assert r.status_code == 400 and r.json()["code"] == "gpx_invalid"
    big = {"file": ("x.gpx", b"x" * (5 * 1024 * 1024 + 1), "application/gpx+xml")}
    r = await client.post(f"{URL}/gpx", files=big, headers=h)
    assert r.status_code == 400 and "5 MB" in r.json()["detail"]
    future = datetime.now(timezone.utc) + timedelta(days=3)
    r = await client.post(f"{URL}/gpx", files=gpx_file(track(26, 100, 30, start=future)), headers=h)
    assert r.json()["code"] == "future_day"


async def test_edit_and_delete(client, session):
    h = await onboard(client)
    run = (
        await client.post(
            f"{URL}/gpx",
            files=gpx_file(track(26, 100, 30, start=yesterday_morning_utc())),
            headers=h,
        )
    ).json()
    rid = run["id"]
    r = await client.patch(f"{URL}/{rid}", json={"distance_m": 3000, "note": "fixed"}, headers=h)
    body = r.json()
    assert body["distance_m"] == 3000
    assert body["calories_kcal"] == round(WEIGHT * 3 * 1.036)
    assert body["duration_s"] == 750  # unchanged
    assert [s["distance_m"] for s in body["splits"]] == [1000, 1000, 1000]
    r = await client.patch(f"{URL}/{rid}", json={"note": None}, headers=h)
    assert r.json()["note"] is None
    future = str(today() + timedelta(days=1))
    assert (await client.patch(f"{URL}/{rid}", json={"day": future}, headers=h)).status_code == 400

    assert (await client.delete(f"{URL}/{rid}", headers=h)).status_code == 204
    assert (await client.get(f"{URL}/{rid}", headers=h)).status_code == 404
    assert await session.scalar(select(func.count()).select_from(RunPoint)) == 0


async def test_isolation_between_users(client, make_client):
    ha = await onboard(client, "a@example.com")
    other = make_client()
    hb = await onboard(other, "b@example.com")
    rid = (await client.post(URL, json=manual(), headers=ha)).json()["id"]

    assert (await other.get(f"{URL}/{rid}", headers=hb)).status_code == 404
    r = await other.patch(f"{URL}/{rid}", json={"distance_m": 100}, headers=hb)
    assert r.status_code == 404
    assert (await other.delete(f"{URL}/{rid}", headers=hb)).status_code == 404
    assert (await other.get(URL, headers=hb)).json() == {"items": [], "total": 0}
    mine = (await client.get(f"{URL}/{rid}", headers=ha)).json()
    assert mine["distance_m"] == 5000
