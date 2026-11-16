from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GymProfile(Base):
    """What Bounce needs to plan gym training."""

    __tablename__ = "gym_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    experience: Mapped[str] = mapped_column(String(16))
    days_per_week: Mapped[int] = mapped_column(Integer)
    session_minutes: Mapped[int] = mapped_column(Integer)
    supplements: Mapped[list] = mapped_column(JSONB, default=list)
    supplements_note: Mapped[str | None] = mapped_column(String(300))
    injuries_note: Mapped[str | None] = mapped_column(String(300))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BouncePlan(Base):
    """A weekly plan written by Bounce. The newest row is the current plan."""

    __tablename__ = "bounce_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(10))
    week_start: Mapped[date] = mapped_column(Date)
    content: Mapped[dict] = mapped_column(JSONB)
    targets: Mapped[dict] = mapped_column(JSONB)
    model: Mapped[str] = mapped_column(String(120))
    based_on_checkin_day: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BounceLetter(Base):
    """A letter from the user's future self, written by Bounce and sealed for 90 days."""

    __tablename__ = "bounce_letters"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    written_on: Mapped[date] = mapped_column(Date)
    open_on: Mapped[date] = mapped_column(Date)
    content: Mapped[dict] = mapped_column(JSONB)  # {"paragraphs": [...]}
    snapshot: Mapped[dict] = mapped_column(JSONB)  # the user's numbers on the day it was written
    model: Mapped[str] = mapped_column(String(120))
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
