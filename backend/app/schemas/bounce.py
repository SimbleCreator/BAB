"""Bounce plan shapes. The model's JSON is validated against these before it is stored."""

import re
from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, Field, field_validator

DayName = Literal["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAYS: tuple[DayName, ...] = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
Mode = Literal["activity", "gym", "both"]
Experience = Literal["beginner", "intermediate", "advanced"]
Supplement = Literal[
    "none",
    "whey_protein",
    "creatine",
    "pre_workout",
    "multivitamin",
    "omega_3",
    "bcaa",
    "mass_gainer",
    "fat_burner",
    "other",
]


# Models make small format slips (a list written as one sentence, a long name, a number
# just out of range). These "lenient" types repair those before validation; anything
# they cannot repair still fails and the reply is rejected.


def _clip(max_len: int):
    def fix(v: Any) -> Any:
        return v.strip()[:max_len] if isinstance(v, str) else v

    return BeforeValidator(fix)


def _clamp(lo: int, hi: int):
    def fix(v: Any) -> Any:
        if isinstance(v, bool) or v is None:
            return v
        try:
            n = round(float(v))
        except (TypeError, ValueError):
            return v
        return min(hi, max(lo, n))

    return BeforeValidator(fix)


_SENTENCES = re.compile(r"\n|;|(?<=[.!?])\s+|\s\u2022\s")
_COMMAS = re.compile(r"\n|;|,(?![^()]*\))|\s\u2022\s")


def _as_list(max_items: int, item_len: int = 200):
    def fix(v: Any) -> Any:
        if isinstance(v, str):
            # Several sentences: one item each. One sentence: a comma-separated list.
            pattern = _SENTENCES if re.search(r"[.!?]\s+\S", v) else _COMMAS
            v = [p.strip(" -*\u2022\t.") for p in pattern.split(v)]
            v = [p for p in v if p]
        if isinstance(v, list):
            v = [x.strip()[:item_len] if isinstance(x, str) else x for x in v][:max_items]
        return v

    return BeforeValidator(fix)


def _first(max_items: int):
    """Keep at most max_items of a list of objects."""
    return BeforeValidator(lambda v: v[:max_items] if isinstance(v, list) else v)


Name = Annotated[str, _clip(60), Field(min_length=1)]
Meal = Annotated[str, _clip(200), Field(min_length=1)]


class ExerciseItem(BaseModel):
    name: Name
    sets: Annotated[int, _clamp(1, 10)]
    reps: Annotated[int | None, _clamp(1, 100)] = None
    seconds: Annotated[int | None, _clamp(5, 900)] = None
    rest_s: Annotated[int | None, _clamp(0, 300)] = None
    notes: Annotated[str | None, _clip(140)] = None


class StretchItem(BaseModel):
    name: Name
    seconds: Annotated[int, _clamp(10, 300)]


class PlanDay(BaseModel):
    day: DayName
    rest: bool = False
    walk_minutes: Annotated[int, _clamp(0, 180)] = 0
    jog_minutes: Annotated[int, _clamp(0, 120)] = 0
    steps_target: Annotated[int, _clamp(0, 30000)] = 0
    home_exercises: Annotated[list[ExerciseItem], _first(10)] = Field(default_factory=list)
    gym_focus: Annotated[str | None, _clip(50)] = None
    gym_exercises: Annotated[list[ExerciseItem], _first(10)] = Field(default_factory=list)
    cardio_minutes: Annotated[int, _clamp(0, 90)] = 0
    stretching: Annotated[list[StretchItem], _first(8)] = Field(default_factory=list)

    @field_validator("rest", mode="before")
    @classmethod
    def _null_false(cls, v: Any) -> Any:
        return False if v is None else v

    @field_validator("walk_minutes", "jog_minutes", "steps_target", "cardio_minutes", mode="before")
    @classmethod
    def _null_zero(cls, v: Any) -> Any:
        return 0 if v is None else v

    @field_validator("home_exercises", "gym_exercises", "stretching", mode="before")
    @classmethod
    def _null_empty(cls, v: Any) -> Any:
        return [] if v is None else v


class MealDay(BaseModel):
    day: DayName
    breakfast: Meal
    lunch: Meal
    snack: Meal
    dinner: Meal


class DietPlan(BaseModel):
    principles: Annotated[list[str], _as_list(6)] = Field(min_length=1)
    eat_more: Annotated[list[str], _as_list(10, 80)] = Field(min_length=1)
    limit: Annotated[list[str], _as_list(10, 80)] = Field(min_length=1)
    days: list[MealDay] = Field(min_length=7, max_length=7)


class PlanContent(BaseModel):
    summary: Annotated[str, _clip(500), Field(min_length=1)]
    days: list[PlanDay] = Field(min_length=7, max_length=7)
    diet: DietPlan
    supplements_advice: Annotated[list[str], _as_list(6, 300)] = Field(default_factory=list)
    tips: Annotated[list[str], _as_list(6)] = Field(min_length=1)

    @field_validator("supplements_advice", mode="before")
    @classmethod
    def _null_empty(cls, v: Any) -> Any:
        return [] if v is None else v

    @field_validator("days")
    @classmethod
    def _week_order(cls, days: list[PlanDay]) -> list[PlanDay]:
        if [d.day for d in days] != list(DAYS):
            raise ValueError("days must be Mon to Sun in order")
        return days


class Targets(BaseModel):
    calories_kcal: int
    protein_g: int
    carbs_g: int
    fat_g: int


class BouncePlanOut(BaseModel):
    id: int
    created_at: datetime
    week_start: date
    mode: Mode
    model: str
    based_on_checkin_day: date | None
    targets: Targets = Field(description="From the nutrition engine, not the model")
    content: PlanContent


class GymProfileIn(BaseModel):
    experience: Experience
    days_per_week: int = Field(ge=1, le=7)
    session_minutes: int = Field(ge=20, le=180)
    supplements: list[Supplement] = Field(default_factory=list, max_length=10)
    supplements_note: str | None = Field(default=None, max_length=300)
    injuries_note: str | None = Field(default=None, max_length=300)

    @field_validator("supplements")
    @classmethod
    def _unique(cls, v: list[str]) -> list[str]:
        v = list(dict.fromkeys(v))
        return ["none"] if "none" in v else v

    @field_validator("supplements_note", "injuries_note")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        v = v.strip() if v else None
        return v or None


class GymProfileOut(GymProfileIn):
    updated_at: datetime


PlanState = Literal["disabled", "none", "active", "checkin_needed", "update_ready"]


class BounceNotificationOut(BaseModel):
    id: str = Field(description="Stable per day and reason; clients may hide it once dismissed")
    kind: Literal["checkin", "meals", "activity", "easy"]
    title: str
    message: str
    action_label: str


class BounceStatusOut(BaseModel):
    enabled: bool = Field(description="False when no AI key is configured")
    mode: Mode
    state: PlanState
    gym_profile_needed: bool
    plan_created_at: datetime | None
    next_update_on: date | None = Field(description="When the weekly update is due")
    plans_left_today: int
    can_generate: bool = Field(
        description="True when POST /bounce/plan would be accepted (ignoring model errors)"
    )
    message: str = Field(description="Bounce's short message for the user right now")
    tips: list[str] = Field(description="Immediate suggestions")
    notification: BounceNotificationOut | None = Field(
        default=None, description="The one thing Bounce wants the user to do now, if any"
    )
