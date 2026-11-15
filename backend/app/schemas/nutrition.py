from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

MealType = Literal["breakfast", "lunch", "snack", "dinner"]


class TargetOut(BaseModel):
    effective_from: date
    calories_kcal: int
    protein_g: int
    carbs_g: int
    fat_g: int
    reason: str


class TargetBreakdownOut(BaseModel):
    """How today's formula target is worked out from the profile (before weekly adjustments)."""

    bmr: int
    activity_factor: float
    maintenance: int
    goal_adjustment: int
    floor: int
    floor_applied: bool
    calories_kcal: int


class TargetsOut(BaseModel):
    current: TargetOut
    breakdown: TargetBreakdownOut
    history: list[TargetOut] = Field(description="Newest first")


class FoodOut(BaseModel):
    kind: Literal["builtin", "custom"]
    food_code: str | None
    custom_food_id: int | None
    name: str
    serving_label: str
    calories_kcal: float = Field(description="Per serving; an estimate")
    protein_g: float
    carbs_g: float
    fat_g: float
    diet_type: str | None
    meal_types: list[str]
    uses: int = Field(description="Times this user has logged it")


class CustomFoodIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    serving_label: str = Field(min_length=1, max_length=40)
    calories_kcal: float = Field(ge=0, le=3000)
    protein_g: float = Field(ge=0, le=300)
    carbs_g: float = Field(ge=0, le=500)
    fat_g: float = Field(ge=0, le=300)

    @field_validator("name", "serving_label")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Cannot be blank.")
        return v

    @field_validator("calories_kcal", "protein_g", "carbs_g", "fat_g")
    @classmethod
    def _one_decimal(cls, v: float) -> float:
        return round(v, 1)


class CustomFoodOut(CustomFoodIn):
    id: int


class ItemIn(BaseModel):
    """Exactly one of food_code (built-in) or custom_food_id."""

    meal_type: MealType
    food_code: str | None = Field(default=None, max_length=40)
    custom_food_id: int | None = None
    servings: float = Field(gt=0, le=20)

    @model_validator(mode="after")
    def _one_food(self) -> "ItemIn":
        if (self.food_code is None) == (self.custom_food_id is None):
            raise ValueError("Send either food_code or custom_food_id.")
        self.servings = round(self.servings, 2)
        return self


class ItemPatch(BaseModel):
    servings: float = Field(gt=0, le=20)


class ItemOut(BaseModel):
    id: int
    food_code: str | None
    custom_food_id: int | None
    name: str
    serving_label: str
    servings: float
    calories_kcal: int
    protein_g: float
    carbs_g: float
    fat_g: float


class Totals(BaseModel):
    calories_kcal: int
    protein_g: float
    carbs_g: float
    fat_g: float


class MealOut(BaseModel):
    meal_type: MealType
    items: list[ItemOut]
    totals: Totals


class DayNutritionOut(BaseModel):
    day: date
    today: date
    target: TargetOut
    eaten: Totals
    remaining_kcal: int = Field(description="Target minus eaten; negative when over")
    meals: list[MealOut] = Field(description="Breakfast, lunch, snack, dinner")


class SuggestionOut(BaseModel):
    food_code: str
    name: str
    serving_label: str
    servings: float
    calories_kcal: int
    protein_g: float


class MealSuggestionsOut(BaseModel):
    meal_type: MealType
    budget_kcal: int
    options: list[SuggestionOut]


class SuggestionsOut(BaseModel):
    day: date
    remaining_kcal: int
    meals: list[MealSuggestionsOut]


class NutritionDayPoint(BaseModel):
    day: date
    calories_kcal: int
    target_kcal: int
    protein_g: float
    has_meals: bool


class NutritionSummaryOut(BaseModel):
    days: list[NutritionDayPoint] = Field(description="Oldest first, ending today")
