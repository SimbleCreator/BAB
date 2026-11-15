from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import DietType, Goal, Level, Sex, TrainingMode


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

    # Stored values are already validated; do not re-check the timezone database on output.
    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str) -> str:
        return v
