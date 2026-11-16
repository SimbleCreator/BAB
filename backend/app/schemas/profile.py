import re
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.content import foods_by_code, region_for, states_by_code
from app.models.enums import DietType, FoodSource, Goal, Level, Sex, TrainingMode, WorkType

USUAL_FOODS_MAX = 12
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    age: int = Field(ge=18, le=100)
    sex: Sex
    height_cm: float = Field(ge=120, le=230, description="Centimetres")
    weight_kg: float = Field(ge=30, le=300, description="Kilograms")
    goal: Goal
    level: Level
    minutes_per_day: int = Field(ge=15, le=120)
    days_per_week: int = Field(ge=2, le=6)
    has_pullup_bar: bool
    diet_type: DietType
    daily_step_goal: int = Field(default=8000, ge=1000, le=50000)
    timezone: str = Field(min_length=1, max_length=64, description="IANA name, e.g. Asia/Kolkata")
    training_mode: TrainingMode = Field(
        default=TrainingMode.activity,
        description="activity (walk, jog, home workouts), gym, or both",
    )
    # "Know me": optional, so older clients keep working.
    city: str | None = Field(default=None, max_length=60)
    state: str | None = Field(
        default=None, description="State or union territory code from /profile/options"
    )
    work_type: WorkType | None = Field(
        default=None, description="desk, standing (on your feet), physical or shifts"
    )
    food_source: FoodSource | None = Field(
        default=None, description="home, hostel (or mess), out (eating out) or mixed"
    )
    wake_time: str | None = Field(default=None, description="Usual wake-up time, HH:MM")
    usual_foods: list[str] = Field(
        default_factory=list,
        max_length=USUAL_FOODS_MAX,
        description="Food codes eaten at home most days",
    )
    sleep_hours: float | None = Field(default=None, ge=3, le=12)
    sweet_drinks_per_day: int | None = Field(
        default=None, ge=0, le=20, description="Sweet tea, coffee or soft drinks a day"
    )
    fasting_note: str | None = Field(default=None, max_length=80)
    food_budget_inr: int | None = Field(
        default=None, ge=50, le=5000, description="Daily food budget in rupees"
    )
    target_weight_kg: float | None = Field(
        default=None, ge=30, le=300, description="Optional goal weight, kilograms"
    )

    @field_validator("target_weight_kg")
    @classmethod
    def _target_one_decimal(cls, v: float | None) -> float | None:
        return None if v is None else round(v, 1)

    @field_validator("city", "fasting_note")
    @classmethod
    def _blank_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("state")
    @classmethod
    def _state(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if v not in states_by_code():
            raise ValueError("Unknown state.")
        return v

    @field_validator("wake_time")
    @classmethod
    def _wake(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not _TIME_RE.match(v):
            raise ValueError("Use HH:MM, for example 06:30.")
        return v

    @field_validator("usual_foods")
    @classmethod
    def _usual(cls, v: list[str]) -> list[str]:
        known = foods_by_code()
        out: list[str] = []
        for code in v:
            if code not in known:
                raise ValueError(f"Unknown food: {code}.")
            if code not in out:
                out.append(code)
        return out

    @field_validator("sleep_hours")
    @classmethod
    def _half_hour(cls, v: float | None) -> float | None:
        return None if v is None else round(v * 2) / 2

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Enter your name.")
        return v

    @field_validator("height_cm", "weight_kg")
    @classmethod
    def _one_decimal(cls, v: float) -> float:
        return round(v, 1)

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Unknown timezone.") from exc
        return v


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)

    updated_at: datetime

    @computed_field(description="Food region from the state; null outside India or unset")
    @property
    def region(self) -> str | None:
        return region_for(self.state)

    # Stored values are already validated; do not re-check them on output (a food code
    # removed from the content later must not break reading the profile).
    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str) -> str:
        return v

    @field_validator("usual_foods")
    @classmethod
    def _usual(cls, v: list[str]) -> list[str]:
        return [c for c in v if c in foods_by_code()]

    @field_validator("state")
    @classmethod
    def _state(cls, v: str | None) -> str | None:
        return v


class StateOption(BaseModel):
    code: str
    name: str
    region: str | None


class ProfileOptionsOut(BaseModel):
    """Choices for the "Know me" questions."""

    states: list[StateOption]
    work_types: list[str]
    food_sources: list[str]
    usual_foods_max: int
