from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ExportOut(BaseModel):
    """Everything stored for the user. Each record is a plain object of stored values."""

    format_version: Literal[1] = 1
    exported_at: datetime
    account: dict[str, Any]
    profile: dict[str, Any] | None
    daily_activity: list[dict[str, Any]]
    runs: list[dict[str, Any]] = Field(description="Each run includes its track points")
    training_plans: list[dict[str, Any]]
    workouts: list[dict[str, Any]] = Field(description="Each workout includes its sets")
    nutrition_targets: list[dict[str, Any]]
    custom_foods: list[dict[str, Any]]
    meals: list[dict[str, Any]] = Field(description="Each meal includes its items")
    checkins: list[dict[str, Any]]
    weekly_adjustments: list[dict[str, Any]]
    milestones: list[dict[str, Any]]
    habits: list[dict[str, Any]] = Field(description="Each plan includes its logs")
    gym_profile: dict[str, Any] | None = None
    bounce_plans: list[dict[str, Any]] = Field(default_factory=list)


class DeleteAccountIn(BaseModel):
    password: str = Field(min_length=1, max_length=128)
    confirm: Literal[True] = Field(description="Must be true: the user confirms permanent removal")


class PublicConfigOut(BaseModel):
    app_name: str
    contact_email: str
    version: str


class WeekCount(BaseModel):
    week_start: date
    count: int


class AdminStatsOut(BaseModel):
    """Aggregates only. No individual's data."""

    total_users: int
    active_7_days: int
    active_30_days: int
    new_users_per_week: list[WeekCount] = Field(description="Last 12 weeks, oldest first")
    records: dict[str, int] = Field(description="Row counts per record type, all users")
