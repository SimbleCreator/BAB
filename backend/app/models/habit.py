from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Habit(Base):
    """A reduction plan. At most one active plan per type per user."""

    __tablename__ = "habits"
    __table_args__ = (
        Index(
            "uq_habits_active_type",
            "user_id",
            "type",
            unique=True,
            postgresql_where=text("active"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(16))  # smoking | drinking
    baseline: Mapped[int] = mapped_column(Integer)
    period: Mapped[str] = mapped_column(String(8))  # day | week
    pace_pct: Mapped[int] = mapped_column(Integer)  # 5 | 10
    started_on: Mapped[date] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class HabitLog(Base):
    __tablename__ = "habit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    habit_id: Mapped[int] = mapped_column(ForeignKey("habits.id", ondelete="CASCADE"))
    day: Mapped[date] = mapped_column(Date)
    units: Mapped[int] = mapped_column(Integer)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_habit_logs_habit_day", "habit_id", "day"),)
