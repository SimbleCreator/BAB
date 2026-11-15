from datetime import datetime

from pydantic import BaseModel, Field

from app.engines.milestone_engine import Category, Unit


class MilestoneOut(BaseModel):
    code: str
    title: str
    description: str
    category: Category
    target: int = Field(description="In `unit` (raw units: steps, metres, counts)")
    current: int = Field(description="Progress so far, capped at target once unlocked")
    unit: Unit
    unlocked_at: datetime | None
    seen: bool = Field(description="False until the user has seen the unlock")


class MilestoneBrief(BaseModel):
    code: str
    title: str
