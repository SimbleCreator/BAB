from datetime import timedelta

import pytest

from app.core.timeutil import local_today
from tests.helpers import PROFILE, bearer, onboard, register

pytestmark = pytest.mark.anyio

TZ = PROFILE["timezone"]  # female, 30, 162 cm, 64.5 kg, lose_fat, 3 days, veg


def day(n: int = 0) -> str:
    return str(local_today(TZ) - timedelta(days=n))


def items_url(n: int = 0) -> str:
    return f"/api/v1/nutrition/days/{day(n)}/items"


async def add(client, h, n=0, **body):
    r = await client.post(
        items_url(n), json={"meal_type": "breakfast", "servings": 1} | body, headers=h
    )
    return r


async def test_targets_created_at_onboarding(client):
    h = await onboard(client)
    t = (await client.get("/api/v1/nutrition/targets", headers=h)).json()
    # BMR 10*64.5 + 6.25*162 - 5*30 - 161 = 1346.5; x1.55 = 2087.1; -400 = 1687
    assert t["current"]["calories_kcal"] == 1687
    assert t["current"]["protein_g"] == 116  # 1.8 g/kg
    assert t["current"]["fat_g"] == 47
    assert t["current"]["carbs_g"] == 200
    assert t["breakdown"]["bmr"] == 1346 or t["breakdown"]["bmr"] == 1347
    assert t["breakdown"]["activity_factor"] == 1.55
    assert t["breakdown"]["goal_adjustment"] == -400
    assert len(t["history"]) == 1


async def test_profile_change_recalculates_today(client):
    h = await onboard(client)
    await client.put("/api/v1/profile", json=PROFILE | {"goal": "build_muscle"}, headers=h)
    t = (await client.get("/api/v1/nutrition/targets", headers=h)).json()
    assert t["current"]["calories_kcal"] == round(1346.5 * 1.55 + 250)
    assert t["current"]["reason"].startswith("Recalculated")
    assert len(t["history"]) == 1  # same day: replaced, not stacked
    await client.put(
        "/api/v1/profile", json=PROFILE | {"goal": "build_muscle", "name": "Z"}, headers=h
    )
    t2 = (await client.get("/api/v1/nutrition/targets", headers=h)).json()
    assert t2["current"] == t["current"]


async def test_floor_applies(client):
    h = await onboard(client, age=80, height_cm=140, weight_kg=38, days_per_week=2)
    t = (await client.get("/api/v1/nutrition/targets", headers=h)).json()
    assert t["current"]["calories_kcal"] == 1200
    assert t["breakdown"]["floor_applied"] is True


async def test_log_edit_delete_items(client):
    h = await onboard(client)
    r = await add(client, h, food_code="idli", servings=1.5)
    assert r.status_code == 201
    d = r.json()
    breakfast = d["meals"][0]
    assert [m["meal_type"] for m in d["meals"]] == ["breakfast", "lunch", "snack", "dinner"]
    assert breakfast["items"][0]["calories_kcal"] == 180  # 120 x 1.5
    assert d["eaten"]["calories_kcal"] == 180
    assert d["remaining_kcal"] == 1687 - 180

    item_id = breakfast["items"][0]["id"]
    r = await client.patch(f"/api/v1/nutrition/items/{item_id}", json={"servings": 3}, headers=h)
    assert r.json()["eaten"]["calories_kcal"] == 360
    r = await client.delete(f"/api/v1/nutrition/items/{item_id}", headers=h)
    assert r.json()["eaten"]["calories_kcal"] == 0
    assert r.json()["meals"][0]["items"] == []


async def test_custom_foods(client):
    h = await onboard(client)
    r = await client.post(
        "/api/v1/foods/custom",
        json={
            "name": " Mom's upma ",
            "serving_label": "1 bowl",
            "calories_kcal": 310,
            "protein_g": 8,
            "carbs_g": 45,
            "fat_g": 11,
        },
        headers=h,
    )
    assert r.status_code == 201
    food = r.json()
    assert food["name"] == "Mom's upma"
    d = (await add(client, h, custom_food_id=food["id"], servings=2)).json()
    assert d["eaten"]["calories_kcal"] == 620
    # Editing or deleting the custom food leaves the logged item as it was.
    await client.put(
        f"/api/v1/foods/custom/{food['id']}", json={**food, "calories_kcal": 100}, headers=h
    )
    assert (await client.delete(f"/api/v1/foods/custom/{food['id']}", headers=h)).status_code == 204
    d = (await client.get(f"/api/v1/nutrition/days/{day()}", headers=h)).json()
    assert d["eaten"]["calories_kcal"] == 620
    assert d["meals"][0]["items"][0]["name"] == "Mom's upma"


async def test_item_rules(client):
    h = await onboard(client)
    future = str(local_today(TZ) + timedelta(days=1))
    r = await client.post(
        f"/api/v1/nutrition/days/{future}/items",
        json={"meal_type": "lunch", "food_code": "idli", "servings": 1},
        headers=h,
    )
    assert r.status_code == 400 and r.json()["code"] == "future_day"
    assert (await add(client, h, food_code="nope")).status_code == 404
    assert (await add(client, h, food_code="idli", custom_food_id=1)).status_code == 422
    assert (await add(client, h)).status_code == 422
    assert (await add(client, h, food_code="idli", servings=0)).status_code == 422
    assert (await add(client, h, food_code="idli", meal_type="brunch")).status_code == 422
    # Past days can be logged.
    assert (await add(client, h, n=10, food_code="idli")).status_code == 201


async def test_food_search_respects_diet_and_puts_recent_first(client):
    h = await onboard(client)  # veg
    foods = (await client.get("/api/v1/foods", params={"q": "chicken"}, headers=h)).json()
    assert foods == []
    egg = (await client.get("/api/v1/foods", params={"q": "egg"}, headers=h)).json()
    assert all(f["diet_type"] == "veg" for f in egg)
    await add(client, h, food_code="sambar", meal_type="lunch")
    first = (await client.get("/api/v1/foods", params={"meal_type": "breakfast"}, headers=h)).json()
    assert first[0]["food_code"] == "sambar" and first[0]["uses"] == 1
    dal = (await client.get("/api/v1/foods", params={"q": "DAL"}, headers=h)).json()
    assert dal and all("dal" in f["name"].lower() for f in dal)


async def test_non_veg_sees_everything(client):
    h = await onboard(client, diet_type="non_veg")
    foods = (await client.get("/api/v1/foods", params={"q": "chicken"}, headers=h)).json()
    assert len(foods) >= 5


async def test_suggestions(client):
    h = await onboard(client)
    s = (await client.get(f"/api/v1/nutrition/days/{day()}/suggestions", headers=h)).json()
    assert [m["meal_type"] for m in s["meals"]] == ["breakfast", "lunch", "snack", "dinner"]
    lunch = s["meals"][1]
    assert lunch["budget_kcal"] == round(1687 * 0.35)
    assert len(lunch["options"]) == 3
    assert all(o["calories_kcal"] <= lunch["budget_kcal"] for o in lunch["options"])
    # After eating almost everything, budgets shrink.
    await add(client, h, food_code="vegetable_biryani", servings=4, meal_type="lunch")
    s = (await client.get(f"/api/v1/nutrition/days/{day()}/suggestions", headers=h)).json()
    assert s["remaining_kcal"] == 1687 - 1600
    assert all(m["budget_kcal"] <= 87 for m in s["meals"])


async def test_summary_and_meal_milestone(client):
    h = await onboard(client)
    for n in range(7):
        await add(client, h, n=n, food_code="banana", meal_type="snack")
    s = (await client.get("/api/v1/nutrition/summary", headers=h)).json()
    assert len(s["days"]) == 7
    assert all(p["calories_kcal"] == 105 and p["target_kcal"] == 1687 for p in s["days"])
    ms = {m["code"]: m for m in (await client.get("/api/v1/milestones", headers=h)).json()}
    assert ms["meals_7_days"]["unlocked_at"] is not None


async def test_today_nutrition(client):
    h = await onboard(client)
    await add(client, h, food_code="poha")
    t = (await client.get("/api/v1/today", headers=h)).json()["nutrition"]
    assert t == {
        "target_kcal": 1687,
        "eaten_kcal": 250,
        "remaining_kcal": 1437,
        "protein_g": 5.0,
        "target_protein_g": 116,
    }


async def test_isolation_between_users(client, make_client):
    ha = await onboard(client, "a@example.com")
    other = make_client()
    hb = await onboard(other, "b@example.com")
    food = (
        await client.post(
            "/api/v1/foods/custom",
            json={
                "name": "Secret",
                "serving_label": "1",
                "calories_kcal": 1,
                "protein_g": 0,
                "carbs_g": 0,
                "fat_g": 0,
            },
            headers=ha,
        )
    ).json()
    item = (await add(client, ha, food_code="idli")).json()["meals"][0]["items"][0]

    assert (await other.get(f"/api/v1/nutrition/days/{day()}", headers=hb)).json()["eaten"][
        "calories_kcal"
    ] == 0
    assert (
        await other.patch(f"/api/v1/nutrition/items/{item['id']}", json={"servings": 9}, headers=hb)
    ).status_code == 404
    assert (
        await other.delete(f"/api/v1/nutrition/items/{item['id']}", headers=hb)
    ).status_code == 404
    assert (await add(other, hb, custom_food_id=food["id"])).status_code == 404
    assert (await other.get("/api/v1/foods/custom", headers=hb)).json() == []
    assert (await other.get("/api/v1/foods", params={"q": "secret"}, headers=hb)).json() == []
    assert (await other.delete(f"/api/v1/foods/custom/{food['id']}", headers=hb)).status_code == 404
    assert (await client.get(f"/api/v1/nutrition/days/{day()}", headers=ha)).json()["eaten"][
        "calories_kcal"
    ] == 120


async def test_requires_profile(client):
    h = bearer(await register(client))
    assert (await client.get(f"/api/v1/nutrition/days/{day()}", headers=h)).status_code == 409
