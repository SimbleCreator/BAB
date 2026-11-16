from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, SessionDep
from app.models.enums import DietType
from app.schemas.common import ErrorOut
from app.schemas.nutrition import (
    CustomFoodIn,
    CustomFoodOut,
    DayNutritionOut,
    FoodOut,
    ItemIn,
    ItemPatch,
    MealType,
    MessPlateIn,
    MessPlateOut,
    NutritionSummaryOut,
    PlateTipsOut,
    StapleOut,
    SuggestionsOut,
    TargetsOut,
)
from app.services import nutrition_service as svc

router = APIRouter(tags=["nutrition"])

_errors = {400: {"model": ErrorOut}, 404: {"model": ErrorOut}, 409: {"model": ErrorOut}}


@router.get("/nutrition/targets", response_model=TargetsOut, responses=_errors)
async def get_targets(user: CurrentUser, session: SessionDep) -> TargetsOut:
    return await svc.get_targets(session, user)


@router.get("/nutrition/days/{day}", response_model=DayNutritionOut, responses=_errors)
async def get_day(day: date, user: CurrentUser, session: SessionDep) -> DayNutritionOut:
    return await svc.get_day(session, user, day)


@router.post(
    "/nutrition/days/{day}/items",
    response_model=DayNutritionOut,
    status_code=status.HTTP_201_CREATED,
    responses=_errors,
    summary="Log a food (built-in or custom) to a meal; returns the updated day",
)
async def add_item(
    day: date, data: ItemIn, user: CurrentUser, session: SessionDep
) -> DayNutritionOut:
    return await svc.add_item(session, user, day, data)


@router.patch("/nutrition/items/{item_id}", response_model=DayNutritionOut, responses=_errors)
async def update_item(
    item_id: int, data: ItemPatch, user: CurrentUser, session: SessionDep
) -> DayNutritionOut:
    return await svc.update_item(session, user, item_id, data)


@router.delete(
    "/nutrition/items/{item_id}",
    response_model=DayNutritionOut,
    responses=_errors,
    summary="Remove a logged item; returns the updated day",
)
async def delete_item(item_id: int, user: CurrentUser, session: SessionDep) -> DayNutritionOut:
    return await svc.delete_item(session, user, item_id)


@router.get("/nutrition/days/{day}/suggestions", response_model=SuggestionsOut, responses=_errors)
async def get_suggestions(day: date, user: CurrentUser, session: SessionDep) -> SuggestionsOut:
    return await svc.suggestions(session, user, day)


@router.get(
    "/nutrition/plate-tips",
    response_model=PlateTipsOut,
    responses=_errors,
    summary="Portion tips for the user's usual home foods (keep the dish, change the amount)",
)
async def plate_tips(user: CurrentUser, session: SessionDep) -> PlateTipsOut:
    return await svc.plate_tips(session, user)


@router.post(
    "/nutrition/days/{day}/mess-plate",
    response_model=MessPlateOut,
    responses=_errors,
    summary="Best plate from what the mess or canteen served, within the meal's budget",
    description="Does not log anything; the app logs the chosen items afterwards.",
)
async def mess_plate(
    day: date, data: MessPlateIn, user: CurrentUser, session: SessionDep
) -> MessPlateOut:
    return await svc.mess_plate(session, user, day, data)


@router.get("/nutrition/summary", response_model=NutritionSummaryOut, responses=_errors)
async def get_summary(
    user: CurrentUser, session: SessionDep, days: Annotated[int, Query(ge=1, le=90)] = 7
) -> NutritionSummaryOut:
    return await svc.summary(session, user, days)


@router.get(
    "/foods",
    response_model=list[FoodOut],
    responses=_errors,
    summary="Built-in foods for the user's diet plus their custom foods; recent and frequent first",
)
async def search_foods(
    user: CurrentUser,
    session: SessionDep,
    q: Annotated[str | None, Query(max_length=60)] = None,
    meal_type: MealType | None = None,
) -> list[FoodOut]:
    return await svc.search_foods(session, user, q, meal_type)


@router.get(
    "/foods/staples",
    response_model=list[StapleOut],
    summary="Dishes to pick usual home foods from (works before onboarding); region first",
)
async def staples(
    user: CurrentUser,
    diet_type: DietType,
    state: Annotated[str | None, Query(max_length=3)] = None,
) -> list[StapleOut]:
    return svc.staples(diet_type.value, state)


@router.get("/foods/custom", response_model=list[CustomFoodOut])
async def list_custom(user: CurrentUser, session: SessionDep) -> list[CustomFoodOut]:
    return await svc.list_custom(session, user)


@router.post("/foods/custom", response_model=CustomFoodOut, status_code=status.HTTP_201_CREATED)
async def create_custom(
    data: CustomFoodIn, user: CurrentUser, session: SessionDep
) -> CustomFoodOut:
    return await svc.create_custom(session, user, data)


@router.put("/foods/custom/{food_id}", response_model=CustomFoodOut, responses=_errors)
async def update_custom(
    food_id: int, data: CustomFoodIn, user: CurrentUser, session: SessionDep
) -> CustomFoodOut:
    return await svc.update_custom(session, user, food_id, data)


@router.delete("/foods/custom/{food_id}", status_code=status.HTTP_204_NO_CONTENT, responses=_errors)
async def delete_custom(food_id: int, user: CurrentUser, session: SessionDep) -> None:
    await svc.delete_custom(session, user, food_id)
