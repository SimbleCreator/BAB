from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class ProjectionOut(BaseModel):
    """How long until the target weight. An estimate, never a promise."""

    status: Literal["no_target", "reached", "on_track", "stalled", "no_gap"] = Field(
        description="no_target: no target weight set; reached: within 0.3 kg; on_track: a "
        "range is given; stalled: the real trend is flat or moving away; no_gap: the calorie "
        "target does not move weight toward the target"
    )
    method: Literal["formula", "trend"] | None = Field(
        description="formula: from the calorie gap; trend: from the user's check-ins"
    )
    current_kg: float
    target_kg: float | None
    kg_to_go: float | None = Field(description="Target minus current; negative to lose")
    weekly_rate_kg: float | None = Field(description="Signed weekly change; negative is loss")
    weeks_min: int | None
    weeks_max: int | None
    date_min: date | None
    date_max: date | None
    too_fast: bool = Field(description="The real trend is faster than the safe rate")
    safe_rate_kg: float = Field(description="Fastest weekly change treated as safe")
    daily_gap_kcal: int = Field(description="Maintenance minus the calorie target")
    checkins_for_trend: int = Field(description="Check-ins still needed before the trend is used")


class ChangeOut(BaseModel):
    name: str = Field(
        description="weight_kg, waist_cm, chest_cm, arms_cm, thighs_cm, energy, sleep or stairs"
    )
    then: float
    now: float
    change: float


class BlockOut(BaseModel):
    start: date
    end: date
    avg_steps: int | None
    workouts: int
    run_km: float
    meal_days: int


class ProgressCardOut(BaseModel):
    number: int
    start: date
    end: date
    then_day: date = Field(description="First check-in")
    now_day: date = Field(description="Latest check-in up to the card's last day")
    measures: list[ChangeOut]
    wins: list[ChangeOut]
    block: BlockOut = Field(description="The card's 4 weeks")
    previous_block: BlockOut | None = Field(description="The 4 weeks before; null on card 1")
    highlights: list[str]


class ProgressOut(BaseModel):
    today: date
    goal: str
    projection: ProjectionOut
    cards: list[ProgressCardOut] = Field(description="Newest first")
    next_card_on: date | None = Field(description="Null until the first check-in")
