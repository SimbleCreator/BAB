from datetime import date, datetime

from pydantic import BaseModel, Field

from app.engines.adjustment_engine import TrainingDecision
from app.schemas.checkin import CheckinOut


class NutritionChangeOut(BaseModel):
    before_kcal: int
    after_kcal: int
    change_kcal: int
    floor_applied: bool
    reason: str


class TrainingChangeOut(BaseModel):
    decision: TrainingDecision
    planned_sessions: int
    done_sessions: int
    completion_pct: int
    changes: list[str] = Field(description="One line per exercise or plan-wide change")
    summary: str


class AdjustmentOut(BaseModel):
    id: int
    checkin_day: date
    reference_day: date = Field(description="The earlier check-in the weight was compared with")
    created_at: datetime
    weekly_change_pct: float = Field(description="+ gain / - loss per week, % of body weight")
    nutrition: NutritionChangeOut
    training: TrainingChangeOut
    summary: list[str] = Field(description="Plain lines to show the user")


class CheckinSavedOut(CheckinOut):
    adjustment: AdjustmentOut | None = Field(
        default=None, description="Set when this check-in triggered the weekly adjustment"
    )
    adjustment_note: str | None = Field(
        default=None, description="Why no adjustment ran, when it did not"
    )
