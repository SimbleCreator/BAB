"""Nutrition targets, foods, meal logging and suggestions."""

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.content import food_list, foods_by_code, region_for
from app.core.errors import AppError, NotFoundError
from app.core.timeutil import local_today
from app.engines import nutrition_engine as eng
from app.engines import plate_engine
from app.models.nutrition import CustomFood, Meal, MealItem, NutritionTarget
from app.models.profile import Profile
from app.models.user import User
from app.repositories import nutrition_repo as repo
from app.schemas.nutrition import (
    CustomFoodIn,
    CustomFoodOut,
    DayNutritionOut,
    FoodOut,
    ItemIn,
    ItemOut,
    ItemPatch,
    MealOut,
    MealSuggestionsOut,
    MessPlateIn,
    MessPlateItemOut,
    MessPlateOut,
    NutritionDayPoint,
    NutritionSummaryOut,
    PlateTipOut,
    PlateTipsOut,
    SkippedFoodOut,
    StapleOut,
    SuggestionOut,
    SuggestionsOut,
    TargetBreakdownOut,
    TargetOut,
    TargetsOut,
    Totals,
)
from app.services import milestone_service
from app.services.common import require_profile

TARGET_FIELDS = ("sex", "age", "height_cm", "weight_kg", "goal", "days_per_week")
SEARCH_LIMIT = 50


# Targets ----------------------------------------------------------------------


def breakdown(profile: Profile) -> eng.TargetBreakdown:
    return eng.targets(
        profile.sex,  # type: ignore[arg-type]
        float(profile.weight_kg),
        float(profile.height_cm),
        profile.age,
        profile.days_per_week,
        profile.goal,
    )


async def set_targets_from_profile(
    session: AsyncSession, user: User, profile: Profile, reason: str
) -> NutritionTarget:
    """Recalculate from the profile, effective today. Replaces a row already set today.
    Does not commit."""
    t = breakdown(profile).targets
    today = local_today(profile.timezone)
    row = await repo.target_on(session, user.id, today)
    if row is None:
        row = NutritionTarget(user_id=user.id, effective_from=today)
        repo.add(session, row)
    row.calories_kcal, row.protein_g = t.calories_kcal, t.protein_g
    row.carbs_g, row.fat_g = t.carbs_g, t.fat_g
    row.reason = reason
    await session.flush()
    return row


async def set_target_calories(
    session: AsyncSession, user: User, profile: Profile, calories: int, reason: str
) -> NutritionTarget:
    """Set a calorie target (from the weekly adjustment), effective today, with macros from
    the current weight and goal. Replaces a row already set today. Does not commit."""
    m = eng.macros_for(calories, float(profile.weight_kg), profile.goal)
    today = local_today(profile.timezone)
    row = await repo.target_on(session, user.id, today)
    if row is None:
        row = NutritionTarget(user_id=user.id, effective_from=today)
        repo.add(session, row)
    row.calories_kcal, row.protein_g, row.carbs_g, row.fat_g = (
        m.calories_kcal,
        m.protein_g,
        m.carbs_g,
        m.fat_g,
    )
    row.reason = reason[:300]
    await session.flush()
    return row


def _target_out(row: NutritionTarget) -> TargetOut:
    return TargetOut(
        effective_from=row.effective_from,
        calories_kcal=row.calories_kcal,
        protein_g=row.protein_g,
        carbs_g=row.carbs_g,
        fat_g=row.fat_g,
        reason=row.reason,
    )


async def _target_row(
    session: AsyncSession, user: User, profile: Profile, day: date
) -> NutritionTarget:
    row = await repo.target_for_day(session, user.id, day)
    if row is None:  # profiles created before targets existed
        row = await set_targets_from_profile(
            session, user, profile, "Starting targets from your profile."
        )
        await session.commit()
    return row


async def get_targets(session: AsyncSession, user: User) -> TargetsOut:
    profile = await require_profile(session, user)
    current = await _target_row(session, user, profile, local_today(profile.timezone))
    b = breakdown(profile)
    return TargetsOut(
        current=_target_out(current),
        breakdown=TargetBreakdownOut(
            bmr=b.bmr,
            activity_factor=b.activity_factor,
            maintenance=b.maintenance,
            goal_adjustment=b.goal_adjustment,
            floor=b.floor,
            floor_applied=b.floor_applied,
            calories_kcal=b.targets.calories_kcal,
        ),
        history=[_target_out(r) for r in await repo.targets(session, user.id)],
    )


# Foods ------------------------------------------------------------------------


def _personal(profile: Profile) -> tuple[frozenset[str], str | None]:
    """The user's usual home foods and food region, used to rank foods."""
    return frozenset(profile.usual_foods or ()), region_for(profile.state)


def _builtin_out(
    f: eng.Food, uses: int, usual: frozenset[str] = frozenset(), region: str | None = None
) -> FoodOut:
    return FoodOut(
        kind="builtin",
        food_code=f.code,
        custom_food_id=None,
        name=f.name,
        serving_label=f.serving_label,
        serving_g=f.serving_g,
        regions=list(f.regions),
        usual=f.code in usual,
        regional=region is not None and region in f.regions,
        calories_kcal=f.calories_kcal,
        protein_g=f.protein_g,
        carbs_g=f.carbs_g,
        fat_g=f.fat_g,
        diet_type=f.diet_type,
        meal_types=list(f.meal_types),
        uses=uses,
    )


def _custom_out(c: CustomFood, uses: int) -> FoodOut:
    return FoodOut(
        kind="custom",
        food_code=None,
        custom_food_id=c.id,
        name=c.name,
        serving_label=c.serving_label,
        serving_g=_opt(c.serving_g),
        calories_kcal=float(c.calories_kcal),
        protein_g=float(c.protein_g),
        carbs_g=float(c.carbs_g),
        fat_g=float(c.fat_g),
        diet_type=None,
        meal_types=list(eng.MEAL_TYPES),
        uses=uses,
    )


async def search_foods(
    session: AsyncSession, user: User, q: str | None, meal_type: str | None
) -> list[FoodOut]:
    """Recent and frequent foods first, then usual home foods, then the user's region, then
    the rest. Built-ins follow the diet type."""
    profile = await require_profile(session, user)
    allowed = eng.ALLOWED_DIETS[profile.diet_type]
    usual, region = _personal(profile)
    usage = await repo.usage(session, user.id)
    query = (q or "").strip().lower()
    never = date.min

    entries: list[tuple[int, date, int, str, FoodOut]] = []
    for f in food_list():
        if f.diet_type not in allowed:
            continue
        if meal_type and not query and meal_type not in f.meal_types:
            continue
        if query and query not in f.name.lower():
            continue
        n, last = usage.get(("builtin", f.code), (0, never))
        out = _builtin_out(f, n, usual, region)
        familiar = 0 if out.usual else 1 if out.regional else 2
        entries.append((n, last, familiar, f.name, out))
    for c in await repo.custom_foods(session, user.id):
        if query and query not in c.name.lower():
            continue
        n, last = usage.get(("custom", c.id), (0, never))
        entries.append((n, last, 1, c.name, _custom_out(c, n)))

    # Used foods first (most recent day, then most uses); then usual home foods, then the
    # user's region (custom foods rank with regional ones); then alphabetical.
    entries.sort(key=lambda e: (e[0] == 0, -e[1].toordinal(), -e[0], e[2], e[3].lower()))
    return [e[4] for e in entries[:SEARCH_LIMIT]]


def staples(diet_type: str, state: str | None) -> list[StapleOut]:
    """Dishes to pick usual home foods from: main meals for the diet type, own region first.

    Works before the profile exists (onboarding)."""
    allowed = eng.ALLOWED_DIETS[diet_type]
    region = region_for(state)
    out = [
        StapleOut(
            food_code=f.code,
            name=f.name,
            serving_label=f.serving_label,
            meal_types=list(f.meal_types),
            regional=region is not None and region in f.regions,
        )
        for f in food_list()
        if f.diet_type in allowed and set(f.meal_types) & {"breakfast", "lunch", "dinner"}
    ]
    out.sort(key=lambda s: (not s.regional, s.name.lower()))
    return out


async def list_custom(session: AsyncSession, user: User) -> list[CustomFoodOut]:
    return [_custom_food_out(c) for c in await repo.custom_foods(session, user.id)]


def _custom_food_out(c: CustomFood) -> CustomFoodOut:
    return CustomFoodOut(
        id=c.id,
        name=c.name,
        serving_label=c.serving_label,
        serving_g=_opt(c.serving_g),
        calories_kcal=float(c.calories_kcal),
        protein_g=float(c.protein_g),
        carbs_g=float(c.carbs_g),
        fat_g=float(c.fat_g),
    )


async def create_custom(session: AsyncSession, user: User, data: CustomFoodIn) -> CustomFoodOut:
    row = CustomFood(user_id=user.id, **data.model_dump())
    repo.add(session, row)
    await session.commit()
    await session.refresh(row)
    return _custom_food_out(row)


async def update_custom(
    session: AsyncSession, user: User, food_id: int, data: CustomFoodIn
) -> CustomFoodOut:
    row = await repo.custom_food(session, user.id, food_id)
    if row is None:
        raise NotFoundError("Food not found.", code="food_missing")
    for k, v in data.model_dump().items():
        setattr(row, k, v)
    await session.commit()
    await session.refresh(row)
    return _custom_food_out(row)


async def delete_custom(session: AsyncSession, user: User, food_id: int) -> None:
    row = await repo.custom_food(session, user.id, food_id)
    if row is None:
        raise NotFoundError("Food not found.", code="food_missing")
    await session.delete(row)  # logged items keep their saved values
    await session.commit()


# Meal logging ------------------------------------------------------------------


def _f(v) -> float:
    return float(v or 0)


def _opt(v) -> float | None:
    return None if v is None else float(v)


def _servings(per: eng.Food, grams: float | None, servings: float | None) -> float:
    """Servings eaten, from grams when given (needs the food's serving weight)."""
    if grams is None:
        return float(servings or 0)
    if per.serving_g <= 0:
        raise AppError(
            "This food has no serving weight. Enter servings, or add its grams per serving.",
            code="no_serving_weight",
        )
    return round(eng.servings_for_grams(per, grams), 2)


def _item_out(i: MealItem) -> ItemOut:
    return ItemOut(
        id=i.id,
        food_code=i.food_code,
        custom_food_id=i.custom_food_id,
        name=i.name,
        serving_label=i.serving_label,
        servings=float(i.servings),
        grams=_opt(i.grams),
        calories_kcal=i.calories_kcal,
        protein_g=_f(i.protein_g),
        carbs_g=_f(i.carbs_g),
        fat_g=_f(i.fat_g),
    )


def _totals(items: list[MealItem]) -> Totals:
    return Totals(
        calories_kcal=sum(i.calories_kcal for i in items),
        protein_g=round(sum(_f(i.protein_g) for i in items), 1),
        carbs_g=round(sum(_f(i.carbs_g) for i in items), 1),
        fat_g=round(sum(_f(i.fat_g) for i in items), 1),
    )


async def get_day(session: AsyncSession, user: User, day: date) -> DayNutritionOut:
    profile = await require_profile(session, user)
    target = await _target_row(session, user, profile, day)
    meals = {m.meal_type: m for m in await repo.meals_on(session, user.id, day)}
    all_items: list[MealItem] = []
    meal_out = []
    for mt in eng.MEAL_TYPES:
        items = list(meals[mt].items) if mt in meals else []
        all_items += items
        meal_out.append(
            MealOut(meal_type=mt, items=[_item_out(i) for i in items], totals=_totals(items))
        )
    eaten = _totals(all_items)
    return DayNutritionOut(
        day=day,
        today=local_today(profile.timezone),
        target=_target_out(target),
        eaten=eaten,
        remaining_kcal=target.calories_kcal - eaten.calories_kcal,
        meals=meal_out,
    )


def _check_day(profile: Profile, day: date) -> None:
    if day > local_today(profile.timezone):
        raise AppError("You cannot log food for a future day.", code="future_day")


async def add_item(session: AsyncSession, user: User, day: date, data: ItemIn) -> DayNutritionOut:
    profile = await require_profile(session, user)
    _check_day(profile, day)
    if data.food_code is not None:
        f = foods_by_code().get(data.food_code)
        if f is None:
            raise NotFoundError("Food not found.", code="food_missing")
        name, label, per = f.name, f.serving_label, f
    else:
        c = await repo.custom_food(session, user.id, data.custom_food_id or 0)
        if c is None:
            raise NotFoundError("Food not found.", code="food_missing")
        name, label = c.name, c.serving_label
        per = eng.Food(
            "",
            c.name,
            c.serving_label,
            _f(c.calories_kcal),
            _f(c.protein_g),
            _f(c.carbs_g),
            _f(c.fat_g),
            "veg",
            (),
            _f(c.serving_g),
        )
    servings = _servings(per, data.grams, data.servings)
    if servings <= 0:
        raise AppError("Enter a bigger amount.", code="amount_too_small")
    m = eng.scale(per, servings)
    meal = await repo.meal(session, user.id, day, data.meal_type)
    if meal is None:
        meal = Meal(user_id=user.id, day=day, meal_type=data.meal_type)
        repo.add(session, meal)
        await session.flush()
    repo.add(
        session,
        MealItem(
            meal_id=meal.id,
            food_code=data.food_code,
            custom_food_id=data.custom_food_id,
            name=name,
            serving_label=label,
            servings=servings,
            grams=data.grams,
            calories_kcal=m.calories_kcal,
            protein_g=m.protein_g,
            carbs_g=m.carbs_g,
            fat_g=m.fat_g,
        ),
    )
    await session.flush()
    await milestone_service.evaluate(session, user.id)
    await session.commit()
    return await get_day(session, user, day)


async def update_item(
    session: AsyncSession, user: User, item_id: int, data: ItemPatch
) -> DayNutritionOut:
    item = await repo.item(session, user.id, item_id)
    if item is None:
        raise NotFoundError("Item not found.", code="item_missing")
    old = float(item.servings)
    if data.grams is not None:
        serving_g = await _serving_g_of(session, user, item)
        if serving_g is None:
            raise AppError(
                "This food has no serving weight. Enter servings instead.",
                code="no_serving_weight",
            )
        new = round(data.grams / serving_g, 2)
    else:
        new = float(data.servings or 0)
    if new <= 0:
        raise AppError("Enter a bigger amount.", code="amount_too_small")
    factor = new / old if old else 1
    item.servings = new  # type: ignore[assignment]
    item.grams = data.grams  # type: ignore[assignment]
    item.calories_kcal = round(item.calories_kcal * factor)
    item.protein_g = round(_f(item.protein_g) * factor, 1)  # type: ignore[assignment]
    item.carbs_g = round(_f(item.carbs_g) * factor, 1)  # type: ignore[assignment]
    item.fat_g = round(_f(item.fat_g) * factor, 1)  # type: ignore[assignment]
    day = item.meal.day
    await session.commit()
    return await get_day(session, user, day)


async def _serving_g_of(session: AsyncSession, user: User, item: MealItem) -> float | None:
    """Grams in one serving for a logged item: from how it was logged, else from the food."""
    if item.grams and float(item.servings):
        return float(item.grams) / float(item.servings)
    if item.food_code:
        f = foods_by_code().get(item.food_code)
        return f.serving_g if f and f.serving_g > 0 else None
    if item.custom_food_id:
        c = await repo.custom_food(session, user.id, item.custom_food_id)
        return float(c.serving_g) if c and c.serving_g else None
    return None


async def delete_item(session: AsyncSession, user: User, item_id: int) -> DayNutritionOut:
    item = await repo.item(session, user.id, item_id)
    if item is None:
        raise NotFoundError("Item not found.", code="item_missing")
    day, meal_id = item.meal.day, item.meal_id
    await session.delete(item)
    await session.flush()
    if await repo.count_items(session, meal_id) == 0:
        await repo.remove_meal(session, meal_id)
    await milestone_service.evaluate(session, user.id)
    await session.commit()
    return await get_day(session, user, day)


# Suggestions and summary ------------------------------------------------------------


async def suggestions(session: AsyncSession, user: User, day: date) -> SuggestionsOut:
    profile = await require_profile(session, user)
    usual, region = _personal(profile)
    d = await get_day(session, user, day)
    out = []
    for mt in eng.MEAL_TYPES:
        budget = eng.meal_budget(d.target.calories_kcal, d.remaining_kcal, mt)
        options = eng.suggest(
            food_list(),
            profile.diet_type,
            mt,
            budget,
            rotation=day.toordinal(),
            usual=usual,
            region=region,
        )
        out.append(
            MealSuggestionsOut(
                meal_type=mt,
                budget_kcal=budget,
                options=[
                    SuggestionOut(
                        food_code=s.food.code,
                        name=s.food.name,
                        serving_label=s.food.serving_label,
                        servings=s.servings,
                        grams=round(s.servings * s.food.serving_g),
                        calories_kcal=s.calories_kcal,
                        protein_g=s.protein_g,
                        why="usual"
                        if s.food.code in usual
                        else "regional"
                        if region is not None and region in s.food.regions
                        else None,
                    )
                    for s in options
                ],
            )
        )
    return SuggestionsOut(day=day, remaining_kcal=d.remaining_kcal, meals=out)


async def summary(session: AsyncSession, user: User, days: int) -> NutritionSummaryOut:
    profile = await require_profile(session, user)
    today = local_today(profile.timezone)
    start = today - timedelta(days=days - 1)
    eaten = await repo.daily_calories(session, user.id, start, today)
    rows = await repo.targets(session, user.id)
    if not rows:
        rows = [await _target_row(session, user, profile, today)]
    points = []
    for i in range(days):
        d = start + timedelta(days=i)
        target = next((r for r in rows if r.effective_from <= d), rows[-1])
        kcal, protein = eaten.get(d, (0, 0.0))
        points.append(
            NutritionDayPoint(
                day=d,
                calories_kcal=kcal,
                target_kcal=target.calories_kcal,
                protein_g=round(protein, 1),
                has_meals=d in eaten,
            )
        )
    return NutritionSummaryOut(days=points)


# Personal plate (M14) -----------------------------------------------------------------


async def plate_tips(session: AsyncSession, user: User) -> PlateTipsOut:
    """Keep-your-plate tips for each usual food: portions and sides, never swaps."""
    profile = await require_profile(session, user)
    by_code = foods_by_code()
    usual = [by_code[c] for c in profile.usual_foods or () if c in by_code]
    return PlateTipsOut(
        goal=profile.goal,
        tips=[
            PlateTipOut(
                food_code=t.food.code,
                name=t.food.name,
                kind=t.kind,
                servings=t.servings,
                grams=t.grams,
                tip=t.tip,
            )
            for t in plate_engine.plate_tips(usual, profile.goal, profile.diet_type)
        ],
    )


async def mess_plate(
    session: AsyncSession, user: User, day: date, data: MessPlateIn
) -> MessPlateOut:
    """The best plate from what the mess or canteen served, within the meal's budget."""
    profile = await require_profile(session, user)
    _check_day(profile, day)
    by_code = foods_by_code()
    allowed = eng.ALLOWED_DIETS[profile.diet_type]
    served = []
    for code in data.food_codes:
        f = by_code.get(code)
        if f is None:
            raise NotFoundError("Food not found.", code="food_missing")
        if f.diet_type in allowed:
            served.append(f)
    d = await get_day(session, user, day)
    budget = eng.meal_budget(d.target.calories_kcal, d.remaining_kcal, data.meal_type)
    plate = plate_engine.mess_plate(served, budget, profile.goal)
    return MessPlateOut(
        meal_type=data.meal_type,
        budget_kcal=budget,
        items=[
            MessPlateItemOut(
                food_code=i.food.code,
                name=i.food.name,
                servings=i.servings,
                grams=i.grams,
                calories_kcal=i.calories_kcal,
                protein_g=i.protein_g,
            )
            for i in plate.items
        ],
        skipped=[SkippedFoodOut(food_code=f.code, name=f.name) for f in plate.skipped],
        calories_kcal=plate.calories_kcal,
        protein_g=plate.protein_g,
    )
