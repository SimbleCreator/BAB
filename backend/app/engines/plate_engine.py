"""Keep-your-plate tips and the best plate from what the mess served.

Familiar food stays: tips change portions and sides, never swap a dish for another.
Foods are sorted into kinds by where their calories come from.
"""

from dataclasses import dataclass
from typing import Literal

from app.engines.nutrition_engine import Food

Kind = Literal["protein", "fatty", "carb", "balanced"]

PROTEIN_SHARE = 0.25  # protein kcal / total kcal at or above: a protein food
FAT_SHARE = 0.45  # fat kcal / total kcal at or above: a rich (fatty) food
CARB_SHARE = 0.60  # carb kcal / total kcal at or above: a carb staple
LIGHT_KCAL = 60  # below this a serving is too light to matter (salad, black coffee)

# Serving changes by goal and kind; None means keep the usual amount.
PORTION: dict[str, dict[Kind, float]] = {
    "lose_fat": {"carb": 0.75, "fatty": 0.5, "protein": 1.25, "balanced": 1.0},
    "build_muscle": {"carb": 1.0, "fatty": 1.0, "protein": 1.5, "balanced": 1.0},
    "stay_fit": {"carb": 1.0, "fatty": 0.75, "protein": 1.0, "balanced": 1.0},
}
PROTEIN_SIDES = {
    "veg": "a bowl of dal, curd or a little paneer",
    "egg": "dal, curd or an egg or two",
    "non_veg": "dal, curd, eggs or a piece of chicken or fish",
}

MESS_STEPS = (0.5, 1.0, 1.5, 2.0)
MESS_MAX_ITEMS = 6


def kind_of(f: Food) -> Kind:
    kcal = f.calories_kcal or 1
    if f.protein_g * 4 / kcal >= PROTEIN_SHARE:
        return "protein"
    if f.fat_g * 9 / kcal >= FAT_SHARE:
        return "fatty"
    if f.carbs_g * 4 / kcal >= CARB_SHARE:
        return "carb"
    return "balanced"


@dataclass(frozen=True)
class PlateTip:
    food: Food
    kind: Kind
    servings: float
    grams: int
    tip: str


def _amount(servings: float) -> str:
    return {
        0.5: "half your usual amount",
        0.75: "about three quarters of your usual amount",
        1.0: "your usual amount",
        1.25: "a little more than usual",
        1.5: "one and a half servings",
    }[servings]


def plate_tip(f: Food, goal: str, diet: str) -> PlateTip:
    kind = kind_of(f)
    servings = PORTION.get(goal, PORTION["stay_fit"])[kind]
    side = PROTEIN_SIDES.get(diet, PROTEIN_SIDES["veg"])
    amount = _amount(servings)
    if f.calories_kcal < LIGHT_KCAL:
        tip = "Keep it as it is. It adds plenty of goodness for very few calories."
        servings = 1.0
    elif kind == "protein":
        tip = f"Keep it and have {amount}: it keeps you full and builds muscle."
    elif kind == "fatty":
        tip = (
            f"Keep it, but have {amount} or make it with less oil or ghee."
            if servings < 1
            else "Keep it. Add a vegetable side to balance the plate."
        )
    elif kind == "carb":
        tip = (
            f"Keep it: have {amount} and add {side}."
            if servings < 1
            else f"Keep your usual amount and add {side} for protein."
        )
    else:
        tip = f"Keep it: {amount}, with a vegetable side."
    return PlateTip(f, kind, servings, round(servings * f.serving_g), tip)


def plate_tips(usual: list[Food], goal: str, diet: str) -> list[PlateTip]:
    return [plate_tip(f, goal, diet) for f in usual]


@dataclass(frozen=True)
class PlateItem:
    food: Food
    servings: float
    grams: int
    calories_kcal: int
    protein_g: float


@dataclass(frozen=True)
class MessPlate:
    items: list[PlateItem]
    skipped: list[Food]
    calories_kcal: int
    protein_g: float
    budget_kcal: int


def mess_plate(served: list[Food], budget_kcal: int, goal: str) -> MessPlate:
    """The best plate from what was served, within the meal's calorie budget.

    Protein foods first, then balanced and carb staples, rich food last. Each gets half a
    serving, then the plate is topped up half a serving at a time in the same order (up
    to 2 servings each) while it stays within budget. Rich food is left at half a
    serving when losing fat. What does not fit is listed as skipped.
    """
    order = {"protein": 0, "balanced": 1, "carb": 2, "fatty": 3}
    foods = sorted(
        {f.code: f for f in served}.values(),
        key=lambda f: (order[kind_of(f)], -f.protein_g / (f.calories_kcal or 1), f.code),
    )[:MESS_MAX_ITEMS]
    servings: dict[str, float] = {}
    total = 0.0
    for f in foods:  # first pass: half a serving of each, in priority order
        if total + 0.5 * f.calories_kcal <= budget_kcal:
            servings[f.code] = 0.5
            total += 0.5 * f.calories_kcal
    grew = True
    while grew:  # then top up in the same order
        grew = False
        for f in foods:
            cur = servings.get(f.code)
            if cur is None or cur >= MESS_STEPS[-1]:
                continue
            if goal == "lose_fat" and kind_of(f) == "fatty":
                continue
            if total + 0.5 * f.calories_kcal <= budget_kcal:
                servings[f.code] = cur + 0.5
                total += 0.5 * f.calories_kcal
                grew = True
    items = [
        PlateItem(
            f,
            servings[f.code],
            round(servings[f.code] * f.serving_g),
            round(servings[f.code] * f.calories_kcal),
            round(servings[f.code] * f.protein_g, 1),
        )
        for f in foods
        if f.code in servings
    ]
    return MessPlate(
        items=items,
        skipped=[f for f in foods if f.code not in servings],
        calories_kcal=sum(i.calories_kcal for i in items),
        protein_g=round(sum(i.protein_g for i in items), 1),
        budget_kcal=budget_kcal,
    )
