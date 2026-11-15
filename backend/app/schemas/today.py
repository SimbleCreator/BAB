from datetime import date

from pydantic import BaseModel, Field

from app.schemas.activity import ActivityOut
from app.schemas.milestone import MilestoneBrief


class TodayOut(BaseModel):
    """Everything for the "what do I do today" screen. Sections grow with each milestone."""

    day: date = Field(description="The user's local date")
    name: str
    line: str = Field(description="Motivational line of the day")
    step_goal: int
    current_streak: int
    activity: ActivityOut | None = Field(description="Null when nothing is logged yet today")
    checkin_due: bool = Field(description="No check-in in the last 7 days")
    new_milestones: list[MilestoneBrief] = Field(description="Unlocked but not seen yet")
