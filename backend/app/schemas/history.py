from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.activity import ActivityOut
from app.schemas.checkin import CheckinOut
from app.schemas.nutrition import DayNutritionOut
from app.schemas.run import RunOut
from app.schemas.training import WorkoutOut


class MonthDayOut(BaseModel):
    day: date
    activity: bool
    workout: Literal["done", "skipped"] | None
    meals: bool
    checkin: bool
    runs: int


class MonthOut(BaseModel):
    month: str = Field(description="YYYY-MM")
    today: date
    days: list[MonthDayOut] = Field(description="Every day of the month, first to last")


class HabitDayOut(BaseModel):
    habit_id: int
    type: str
    units: int


class HistoryDayOut(BaseModel):
    day: date
    today: date
    activity: ActivityOut | None
    runs: list[RunOut]
    workout_title: str | None = Field(description="The planned session for the day, if any")
    workout: WorkoutOut | None
    nutrition: DayNutritionOut
    checkin: CheckinOut | None
    habits: list[HabitDayOut]
