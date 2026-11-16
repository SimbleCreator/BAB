"""Calorie and macro targets, and meal suggestions.

Formula-based; see docs/rules.md, section "Nutrition". Estimates only.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

Sex = Literal["male", "female"]
MealType = Literal["breakfast", "lunch", "dinner", "snack"]
MEAL_TYPES: tuple[MealType, ...] = ("breakfast", "lunch", "snack", "dinner")

GOAL_ADJUSTMENT = {"lose_fat": -400, "build_muscle": 250, "stay_fit": 0}
CALORIE_FLOOR = {"male": 1500, "female": 1200}
PROTEIN_G_PER_KG = {"lose_fat": 1.8, "build_muscle": 1.6, "stay_fit": 1.6}
FAT_SHARE = 0.25
KCAL_PER_G = {"protein": 4, "carbs": 4, "fat": 9}

# Share of the day's calories each meal aims for (used for suggestions).
MEAL_SHARE: dict[MealType, float] = {
    "breakfast": 0.25,
    "lunch": 0.35,
    "snack": 0.10,
    "dinner": 0.30,
}
SUGGESTIONS_PER_MEAL = 3
SERVING_STEPS = (0.5, 1.0, 1.5)
# Each half serving away from 1 counts like 12.5% of the budget left unused, so a normal
# single serving is preferred over doubling a dish just to fill the budget.
SERVING_PENALTY_PER_STEP = 0.125
# Familiar food first: usual home dishes, then dishes from the user's region, as long as
# they fill at least this share of the meal's budget.
FAMILIAR_MIN_FILL = 0.5
# Logging by weight: allowed grams for one item.
GRAMS_MIN = 1
GRAMS_MAX = 3000

# Which diets may eat which foods.
ALLOWED_DIETS = {"veg": {"veg"}, "egg": {"veg", "egg"}, "non_veg": {"veg", "egg", "non_veg"}}


def bmr(sex: Sex, weight_kg: float, height_cm: float, age: int) -> float:
    """Mifflin-St Jeor: 10 x kg + 6.25 x cm - 5 x age, +5 for men, -161 for women."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if sex == "male" else base - 161


def activity_factor(days_per_week: int) -> float:
    if days_per_week <= 2:
        return 1.375
    if days_per_week <= 4:
        return 1.55
    return 1.725


@dataclass(frozen=True)
class Macros:
    calories_kcal: int
    protein_g: int
    carbs_g: int
    fat_g: int


@dataclass(frozen=True)
class TargetBreakdown:
    bmr: int
    activity_factor: float
    maintenance: int
    goal_adjustment: int
    floor: int
    floor_applied: bool
    targets: Macros


def floor_for(sex: Sex) -> int:
    return CALORIE_FLOOR[sex]


def macros_for(calories: int, weight_kg: float, goal: str) -> Macros:
    """Protein by body weight, fat 25% of calories, carbs the remainder (never negative)."""
    protein = round(PROTEIN_G_PER_KG[goal] * weight_kg)
    fat = round(calories * FAT_SHARE / KCAL_PER_G["fat"])
    carbs_kcal = calories - protein * KCAL_PER_G["protein"] - fat * KCAL_PER_G["fat"]
    carbs = max(0, round(carbs_kcal / KCAL_PER_G["carbs"]))
    return Macros(calories, protein, carbs, fat)


def targets(
    sex: Sex, weight_kg: float, height_cm: float, age: int, days_per_week: int, goal: str
) -> TargetBreakdown:
    b = bmr(sex, weight_kg, height_cm, age)
    factor = activity_factor(days_per_week)
    maintenance = b * factor
    adjustment = GOAL_ADJUSTMENT[goal]
    floor = floor_for(sex)
    raw = round(maintenance + adjustment)
    calories = max(raw, floor)
    return TargetBreakdown(
        bmr=round(b),
        activity_factor=factor,
        maintenance=round(maintenance),
        goal_adjustment=adjustment,
        floor=floor,
        floor_applied=raw < floor,
        targets=macros_for(calories, weight_kg, goal),
    )


# Suggestions --------------------------------------------------------------------


@dataclass(frozen=True)
class Food:
    code: str
    name: str
    serving_label: str
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    diet_type: str
    meal_types: tuple[str, ...]
    serving_g: float = 0
    regions: tuple[str, ...] = ()


@dataclass(frozen=True)
class Suggestion:
    food: Food
    servings: float
    calories_kcal: int
    protein_g: float


def meal_budget(target_kcal: int, remaining_kcal: int, meal: MealType) -> int:
    """Calories to aim for at this meal: its share of the day, capped by what is left."""
    return max(0, min(remaining_kcal, round(target_kcal * MEAL_SHARE[meal])))


def suggest(
    foods: Sequence[Food],
    diet_type: str,
    meal: MealType,
    budget_kcal: int,
    rotation: int = 0,
    count: int = SUGGESTIONS_PER_MEAL,
    usual: frozenset[str] = frozenset(),
    region: str | None = None,
) -> list[Suggestion]:
    """Up to `count` foods for a meal that fit the diet and come close to the budget.

    Each food gets the serving size (0.5, 1 or 1.5) that best balances filling the budget
    against staying near a normal single serving, without going over; foods that cannot
    fit even at half a serving are left out. The best
    matches (closest to budget, then most protein per kcal) form a short list, and
    `rotation` (for example the day number) picks a different few from it each day.

    Familiar food first: foods the user eats at home (`usual`) rank ahead of dishes from
    the user's `region`, which rank ahead of the rest, provided they fill at least
    FAMILIAR_MIN_FILL of the budget; within a tier the closest fit wins.
    """
    allowed = ALLOWED_DIETS[diet_type]
    scored: list[tuple[int, float, float, Suggestion]] = []
    for f in foods:
        if f.diet_type not in allowed or meal not in f.meal_types or f.calories_kcal <= 0:
            continue
        fitting = [s for s in SERVING_STEPS if s * f.calories_kcal <= budget_kcal]
        if not fitting:
            continue

        def cost(s: float, kcal_per: float = f.calories_kcal) -> float:
            unused = (budget_kcal - s * kcal_per) / budget_kcal
            return unused + SERVING_PENALTY_PER_STEP * abs(s - 1) / 0.5

        servings = min(fitting, key=lambda s: (cost(s), -s))
        kcal = servings * f.calories_kcal
        gap = cost(servings)
        tier = familiarity(f, usual, region) if kcal >= FAMILIAR_MIN_FILL * budget_kcal else 2
        protein_density = f.protein_g / f.calories_kcal
        scored.append(
            (
                tier,
                round(gap, 2),
                -protein_density,
                Suggestion(f, servings, round(kcal), round(servings * f.protein_g, 1)),
            )
        )
    scored.sort(key=lambda t: (t[0], t[1], t[2], t[3].food.code))
    shortlist = [s for *_, s in scored[: count * 3]]
    if not shortlist:
        return []
    start = (rotation * count) % len(shortlist)
    rotated = shortlist[start:] + shortlist[:start]
    return rotated[:count]


def familiarity(food: Food, usual: frozenset[str], region: str | None) -> int:
    """0 for a usual home food, 1 for a dish from the user's region, 2 otherwise."""
    if food.code in usual:
        return 0
    if region is not None and region in food.regions:
        return 1
    return 2


def servings_for_grams(food: Food, grams: float) -> float:
    """Servings eaten for a weight in grams. Needs the food's serving weight."""
    if food.serving_g <= 0:
        raise ValueError("This food has no serving weight.")
    return grams / food.serving_g


def scale(food: Food, servings: float) -> Macros:
    return Macros(
        calories_kcal=round(food.calories_kcal * servings),
        protein_g=round(food.protein_g * servings, 1),  # type: ignore[arg-type]
        carbs_g=round(food.carbs_g * servings, 1),  # type: ignore[arg-type]
        fat_g=round(food.fat_g * servings, 1),  # type: ignore[arg-type]
    )
