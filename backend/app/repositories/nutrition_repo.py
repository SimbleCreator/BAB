from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.nutrition import CustomFood, Meal, MealItem, NutritionTarget


async def targets(session: AsyncSession, user_id: int) -> list[NutritionTarget]:
    rows = await session.scalars(
        select(NutritionTarget)
        .where(NutritionTarget.user_id == user_id)
        .order_by(NutritionTarget.effective_from.desc(), NutritionTarget.id.desc())
    )
    return list(rows)


async def target_for_day(session: AsyncSession, user_id: int, day: date) -> NutritionTarget | None:
    row = await session.scalar(
        select(NutritionTarget)
        .where(NutritionTarget.user_id == user_id, NutritionTarget.effective_from <= day)
        .order_by(NutritionTarget.effective_from.desc(), NutritionTarget.id.desc())
        .limit(1)
    )
    if row is not None:
        return row
    # Days before the first target use the first target.
    return await session.scalar(
        select(NutritionTarget)
        .where(NutritionTarget.user_id == user_id)
        .order_by(NutritionTarget.effective_from, NutritionTarget.id)
        .limit(1)
    )


async def target_on(session: AsyncSession, user_id: int, day: date) -> NutritionTarget | None:
    return await session.scalar(
        select(NutritionTarget).where(
            NutritionTarget.user_id == user_id, NutritionTarget.effective_from == day
        )
    )


def add(session: AsyncSession, row) -> None:
    session.add(row)


async def meals_on(session: AsyncSession, user_id: int, day: date) -> list[Meal]:
    rows = await session.scalars(
        select(Meal)
        .where(Meal.user_id == user_id, Meal.day == day)
        .options(selectinload(Meal.items))
        .execution_options(populate_existing=True)
    )
    return list(rows)


async def meal(session: AsyncSession, user_id: int, day: date, meal_type: str) -> Meal | None:
    return await session.scalar(
        select(Meal).where(Meal.user_id == user_id, Meal.day == day, Meal.meal_type == meal_type)
    )


async def item(session: AsyncSession, user_id: int, item_id: int) -> MealItem | None:
    return await session.scalar(
        select(MealItem)
        .join(Meal)
        .where(MealItem.id == item_id, Meal.user_id == user_id)
        .options(selectinload(MealItem.meal))
    )


async def count_items(session: AsyncSession, meal_id: int) -> int:
    return await session.scalar(select(func.count()).where(MealItem.meal_id == meal_id)) or 0


async def remove_meal(session: AsyncSession, meal_id: int) -> None:
    await session.execute(delete(Meal).where(Meal.id == meal_id))


async def daily_calories(
    session: AsyncSession, user_id: int, start: date, end: date
) -> dict[date, tuple[int, float]]:
    rows = await session.execute(
        select(Meal.day, func.sum(MealItem.calories_kcal), func.sum(MealItem.protein_g))
        .join(MealItem)
        .where(Meal.user_id == user_id, Meal.day >= start, Meal.day <= end)
        .group_by(Meal.day)
    )
    return {d: (int(k or 0), float(p or 0)) for d, k, p in rows.all()}


async def usage(
    session: AsyncSession, user_id: int
) -> dict[tuple[str, str | int], tuple[int, date]]:
    """(kind, key) -> (times logged, last day) for foods this user has logged."""
    rows = await session.execute(
        select(MealItem.food_code, MealItem.custom_food_id, func.count(), func.max(Meal.day))
        .join(Meal)
        .where(Meal.user_id == user_id)
        .group_by(MealItem.food_code, MealItem.custom_food_id)
    )
    out: dict[tuple[str, str | int], tuple[int, date]] = {}
    for code, custom_id, n, last in rows.all():
        if code:
            out[("builtin", code)] = (n, last)
        elif custom_id:
            out[("custom", custom_id)] = (n, last)
    return out


async def meal_days(session: AsyncSession, user_id: int) -> int:
    return (
        await session.scalar(
            select(func.count(func.distinct(Meal.day)))
            .select_from(Meal)
            .join(MealItem)
            .where(Meal.user_id == user_id)
        )
        or 0
    )


async def custom_foods(session: AsyncSession, user_id: int) -> list[CustomFood]:
    rows = await session.scalars(
        select(CustomFood).where(CustomFood.user_id == user_id).order_by(CustomFood.name)
    )
    return list(rows)


async def custom_food(session: AsyncSession, user_id: int, food_id: int) -> CustomFood | None:
    return await session.scalar(
        select(CustomFood).where(CustomFood.id == food_id, CustomFood.user_id == user_id)
    )


async def meal_types_by_day(
    session: AsyncSession, user_id: int, start: date, end: date
) -> dict[date, int]:
    """Number of meals with at least one item, per day."""
    rows = await session.execute(
        select(Meal.day, func.count(func.distinct(Meal.meal_type)))
        .join(MealItem)
        .where(Meal.user_id == user_id, Meal.day >= start, Meal.day <= end)
        .group_by(Meal.day)
    )
    return {d: int(n) for d, n in rows.all()}
