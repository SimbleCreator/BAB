import pytest

from app.content import food_list
from app.engines import nutrition_engine as eng

FOODS = food_list()


def test_bmr_mifflin_st_jeor():
    # 10 x 70 + 6.25 x 175 - 5 x 30 = 1643.75
    assert eng.bmr("male", 70, 175, 30) == pytest.approx(1648.75)
    assert eng.bmr("female", 70, 175, 30) == pytest.approx(1482.75)


@pytest.mark.parametrize(
    ("days", "factor"), [(0, 1.375), (2, 1.375), (3, 1.55), (4, 1.55), (5, 1.725), (6, 1.725)]
)
def test_activity_factor(days, factor):
    assert eng.activity_factor(days) == factor


@pytest.mark.parametrize(
    ("goal", "adj"), [("lose_fat", -400), ("build_muscle", 250), ("stay_fit", 0)]
)
def test_goal_adjustment(goal, adj):
    t = eng.targets("male", 70, 175, 30, 3, goal)
    assert t.goal_adjustment == adj
    assert t.targets.calories_kcal == round(1648.75 * 1.55 + adj)
    assert t.maintenance == round(1648.75 * 1.55)


def test_floors():
    small_woman = eng.targets("female", 40, 145, 70, 2, "lose_fat")
    assert small_woman.targets.calories_kcal == 1200 and small_woman.floor_applied
    small_man = eng.targets("male", 45, 150, 80, 2, "lose_fat")
    assert small_man.targets.calories_kcal == 1500 and small_man.floor_applied
    assert not eng.targets("male", 80, 180, 25, 4, "stay_fit").floor_applied


def test_macros():
    m = eng.macros_for(2000, 70, "lose_fat")
    assert m.protein_g == 126  # 1.8 g/kg
    assert m.fat_g == round(2000 * 0.25 / 9)  # 56
    assert m.carbs_g == round((2000 - 126 * 4 - 56 * 9) / 4)
    assert eng.macros_for(2000, 70, "build_muscle").protein_g == 112  # 1.6 g/kg
    assert eng.macros_for(2000, 70, "stay_fit").protein_g == 112


def test_carbs_never_negative():
    assert eng.macros_for(1200, 150, "lose_fat").carbs_g == 0


def test_food_list():
    assert len(FOODS) >= 150
    assert {f.diet_type for f in FOODS} == {"veg", "egg", "non_veg"}


def test_meal_budget():
    assert eng.meal_budget(2000, 2000, "lunch") == 700
    assert eng.meal_budget(2000, 300, "lunch") == 300
    assert eng.meal_budget(2000, -50, "dinner") == 0


@pytest.mark.parametrize("diet", ["veg", "egg", "non_veg"])
@pytest.mark.parametrize("meal", eng.MEAL_TYPES)
def test_suggestions_match_diet_meal_and_budget(diet, meal):
    budget = 500
    out = eng.suggest(FOODS, diet, meal, budget)
    assert len(out) == 3
    assert len({s.food.code for s in out}) == 3
    for s in out:
        assert s.food.diet_type in eng.ALLOWED_DIETS[diet]
        assert meal in s.food.meal_types
        assert s.calories_kcal <= budget
        assert s.servings in eng.SERVING_STEPS


def test_veg_never_gets_egg_or_meat():
    for rotation in range(10):
        out = eng.suggest(FOODS, "veg", "dinner", 600, rotation)
        assert all(s.food.diet_type == "veg" for s in out)


def test_suggestions_rotate_by_day():
    a = eng.suggest(FOODS, "non_veg", "lunch", 700, 0)
    b = eng.suggest(FOODS, "non_veg", "lunch", 700, 1)
    assert [s.food.code for s in a] != [s.food.code for s in b]


def test_small_budget_gives_small_foods_or_nothing():
    out = eng.suggest(FOODS, "veg", "snack", 60)
    assert all(s.calories_kcal <= 60 for s in out)
    assert eng.suggest(FOODS, "veg", "snack", 0) == []


def test_scale():
    banana = next(f for f in FOODS if f.code == "banana")
    m = eng.scale(banana, 2)
    assert m.calories_kcal == 210 and m.protein_g == 2.6


def test_prefers_a_normal_serving():
    out = eng.suggest(FOODS, "non_veg", "lunch", 910)
    assert all(s.servings <= 1.5 for s in out)
    assert any(s.servings == 1 for s in eng.suggest(FOODS, "veg", "lunch", 450))


# Personal B.A.B (M11) --------------------------------------------------------------


def _food(code, kcal, regions=(), serving_g=100.0):
    return eng.Food(code, code, "1 bowl", kcal, 10, 30, 5, "veg", ("lunch",), serving_g, regions)


def test_content_has_regional_dishes_with_weights():
    from app.content import REGIONS, states

    foods = food_list()
    assert len(foods) >= 250
    assert all(f.serving_g > 0 for f in foods)
    for region in REGIONS:
        assert sum(region in f.regions for f in foods) >= 5, region
    assert {s.region for s in states()} == {*REGIONS, None}


def test_region_for_state():
    from app.content import region_for

    assert region_for("KA") == "south"
    assert region_for("WB") == "east"
    assert region_for("OUT") is None
    assert region_for(None) is None
    assert region_for("XX") is None


def test_familiarity():
    usual = frozenset({"a"})
    assert eng.familiarity(_food("a", 300, ("south",)), usual, "south") == 0
    assert eng.familiarity(_food("b", 300, ("south",)), usual, "south") == 1
    assert eng.familiarity(_food("b", 300, ("south",)), usual, "north") == 2
    assert eng.familiarity(_food("b", 300, ("south",)), usual, None) == 2


def test_usual_and_regional_food_lead_suggestions():
    plain = _food("plain", 400)  # fills the budget exactly
    regional = _food("regional", 300, ("east",))  # 1 serving fills 75%
    usual = _food("usual", 270)  # 1 serving fills 67.5%
    tiny = _food("tiny", 60, ("east",))  # 1.5 servings fill only 22.5%: not preferred
    foods = [plain, regional, usual, tiny]

    def first(**kw):
        return eng.suggest(foods, "veg", "lunch", 400, count=1, **kw)[0].food.code

    assert first() == "plain"
    assert first(region="east") == "regional"
    assert first(region="east", usual=frozenset({"usual"})) == "usual"
    order = [s.food.code for s in eng.suggest(foods, "veg", "lunch", 400, count=4, region="east")]
    assert order[:2] == ["regional", "plain"]
    assert order[-1] == "tiny"


def test_servings_for_grams():
    f = _food("x", 200, serving_g=150)
    assert eng.servings_for_grams(f, 300) == 2
    assert eng.servings_for_grams(f, 75) == 0.5
    with pytest.raises(ValueError):
        eng.servings_for_grams(_food("y", 200, serving_g=0), 100)
