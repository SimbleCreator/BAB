from app.content import foods_by_code
from app.engines import plate_engine as pe
from app.engines.nutrition_engine import Food


def f(code, kcal, p, c, fat, serving_g=100):
    return Food(code, code, "1 bowl", kcal, p, c, fat, "veg", ("lunch",), serving_g, ())


RICE = f("rice", 200, 4, 45, 0.5, 160)  # carb
PANEER = f("paneer", 265, 18, 3, 20)  # protein 27% is checked before fat 68%
DAL = f("dal", 180, 12, 22, 4, 200)  # protein share 27%: protein
SAMOSA = f("samosa", 260, 4, 30, 14, 100)  # fat 48%: fatty
SALAD = f("salad", 50, 2, 8, 1, 150)
SABZI = f("sabzi", 180, 5, 18, 7, 180)  # balanced


def test_kinds():
    assert pe.kind_of(RICE) == "carb"
    assert pe.kind_of(DAL) == "protein"
    assert pe.kind_of(SAMOSA) == "fatty" and pe.kind_of(PANEER) == "protein"
    assert pe.kind_of(SABZI) == "balanced"


def test_lose_fat_keeps_the_dish_and_changes_portion():
    rice = pe.plate_tip(RICE, "lose_fat", "veg")
    assert (rice.servings, rice.grams) == (0.75, 120)
    assert rice.tip.startswith("Keep it") and "dal, curd" in rice.tip
    assert pe.plate_tip(SAMOSA, "lose_fat", "veg").servings == 0.5
    assert pe.plate_tip(DAL, "lose_fat", "veg").servings == 1.25
    assert pe.plate_tip(SALAD, "lose_fat", "veg").servings == 1


def test_build_muscle_and_diet_sides():
    assert pe.plate_tip(DAL, "build_muscle", "veg").servings == 1.5
    rice = pe.plate_tip(RICE, "build_muscle", "non_veg")
    assert rice.servings == 1 and "chicken or fish" in rice.tip
    assert "egg" in pe.plate_tip(RICE, "build_muscle", "egg").tip


def test_every_food_gets_a_tip():
    for food in foods_by_code().values():
        for goal in ("lose_fat", "build_muscle", "stay_fit"):
            t = pe.plate_tip(food, goal, "non_veg")
            assert t.tip and t.grams >= 0


def test_mess_plate_protein_first_within_budget():
    plate = pe.mess_plate([RICE, SAMOSA, DAL, SABZI], 600, "lose_fat")
    names = [i.food.code for i in plate.items]
    assert names[0] == "dal"
    assert plate.calories_kcal <= 600
    samosa = next(i for i in plate.items if i.food.code == "samosa")
    assert samosa.servings == 0.5  # rich food stays at half a serving when losing fat
    dal = next(i for i in plate.items if i.food.code == "dal")
    assert dal.servings >= 1


def test_mess_plate_skips_what_does_not_fit():
    plate = pe.mess_plate([DAL, RICE, SAMOSA], 200, "stay_fit")
    assert [i.food.code for i in plate.items] == ["dal", "rice"]
    assert [s.code for s in plate.skipped] == ["samosa"]
    assert plate.calories_kcal == 190


def test_mess_plate_caps_servings_and_items():
    plate = pe.mess_plate([DAL], 5000, "build_muscle")
    assert plate.items[0].servings == 2.0
    many = [f(f"x{i}", 100, 5, 10, 2) for i in range(10)]
    assert len(pe.mess_plate(many, 5000, "stay_fit").items) == pe.MESS_MAX_ITEMS
