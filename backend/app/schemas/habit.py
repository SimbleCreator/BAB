from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

HabitType = Literal["smoking", "drinking"]


class HabitIn(BaseModel):
    type: HabitType
    baseline: int = Field(
        ge=1, le=100, description="Usual amount: cigarettes per day, or drinks per week"
    )
    pace_pct: Literal[5, 10] = Field(description="5 = gentle, 10 = standard (% of baseline/week)")


class HabitOut(BaseModel):
    id: int
    type: HabitType
    period: Literal["day", "week"]
    baseline: int
    pace_pct: int
    started_on: date
    active: bool


class GoalsOut(BaseModel):
    steps: bool = Field(description="Step goal met")
    workout: bool = Field(description="Planned workout done, or a rest day")
    meals: bool = Field(description="At least two meals logged")
    met: int


class AvailabilityOut(BaseModel):
    period: Literal["day", "week"] = Field(description="Today for smoking, this week for drinking")
    allowance: int
    unlocked: int
    available_now: int
    locked: int
    used: int
    over: int = Field(description="Units above the allowance; shown without judgement")


class WeekResultOut(BaseModel):
    number: int = Field(description="1 for the first week of the plan")
    start: date
    end: date
    step: int
    allowance_total: int
    used: int
    within: bool
    avoided: int = Field(description="Units below the baseline for the week, when within")


class HabitStatusOut(BaseModel):
    habit: HabitOut
    today: date
    week_number: int
    week_start: date
    week_end: date
    allowance_per_period: int
    week_allowance: int
    week_used: int
    today_used: int
    availability: AvailabilityOut
    goals_today: GoalsOut
    last_week: WeekResultOut | None
    doctor_line: str


class DayUnitsIn(BaseModel):
    units: int = Field(ge=0, le=200)


class LogIn(BaseModel):
    day: date | None = Field(default=None, description="Defaults to today")


class DayLogOut(BaseModel):
    day: date
    units: int
