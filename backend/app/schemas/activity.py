from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import Source

MAX_STEPS = 200_000
MAX_DISTANCE_M = 300_000
MAX_ACTIVE_KCAL = 20_000


class ActivityIn(BaseModel):
    """Leave a field null to have it estimated (distance, calories) or unknown."""

    steps: int | None = Field(default=None, ge=0, le=MAX_STEPS)
    distance_m: int | None = Field(default=None, ge=0, le=MAX_DISTANCE_M, description="Metres")
    active_kcal: int | None = Field(default=None, ge=0, le=MAX_ACTIVE_KCAL)
    note: str | None = Field(default=None, max_length=500)

    @field_validator("note")
    @classmethod
    def _note(cls, v: str | None) -> str | None:
        v = v.strip() if v else None
        return v or None

    @model_validator(mode="after")
    def _something(self) -> "ActivityIn":
        if self.steps is None and self.distance_m is None and self.active_kcal is None:
            raise ValueError("Enter at least one of steps, distance or active calories.")
        return self


class ActivityOut(BaseModel):
    day: date
    steps: int | None
    distance_m: int | None
    active_kcal: int | None
    distance_estimated: bool = Field(description="True when distance was estimated from steps")
    active_kcal_estimated: bool = Field(description="True when calories were estimated")
    source: Source
    note: str | None
    updated_at: datetime


class DayPoint(BaseModel):
    day: date
    has_entry: bool
    steps: int = Field(description="0 when nothing was logged")
    distance_m: int
    active_kcal: int
    goal_met: bool


class ActivitySummaryOut(BaseModel):
    today: date = Field(description="The user's local date")
    step_goal: int
    current_streak: int = Field(description="Consecutive days meeting the step goal")
    longest_streak: int
    total_steps: int = Field(description="Sum over the returned days")
    total_distance_m: int
    days: list[DayPoint] = Field(description="Oldest first, one point per day, ending today")


class CsvRowOut(BaseModel):
    line: int
    day: date | None
    steps: int | None
    distance_m: int | None
    active_kcal: int | None
    errors: list[str]
    exists: bool = Field(description="A record already exists for this day")


class CsvPreviewOut(BaseModel):
    file_errors: list[str]
    rows: list[CsvRowOut]
    valid_rows: int
    invalid_rows: int
    existing_rows: int


class CsvImportOut(BaseModel):
    created: int
    updated: int
    skipped_existing: int
    skipped_invalid: int


class DrillOut(BaseModel):
    code: str
    name: str
    seconds: int
    instructions: str


class EasyDayOut(BaseModel):
    """The "Easy day": a 10-minute plan that still counts for the step-goal streak."""

    day: date
    taken: bool = Field(description="Today is an easy day")
    left_this_week: int = Field(description="Easy days still available this week (Mon-Sun)")
    per_week: int
    suggested: bool = Field(description="Nothing was logged on each of the last 3 days")
    minutes: int
    plan: list[DrillOut]
